from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from cico_pipeline.clients import chat_completion, embeddings
from cico_pipeline.io import query_cache_dir, read_json, repo_cache_dir, stable_hash, write_json
from utils.text_util import extract_code_blocks


def get_parser(language: str):
    if language == "py":
        from parser.py_parser import PyParser

        return PyParser()
    if language == "java":
        from parser.java_parser import JavaParser

        return JavaParser()
    if language == "go":
        from parser.go_parser import GoParser

        return GoParser()
    raise ValueError(f"Unsupported language: {language}")


def parse_repo(repo_path: str, language: str, cache_dir: Path, force: bool = False) -> list[dict[str, Any]]:
    path = cache_dir / "functions.json"
    if path.exists() and not force:
        return read_json(path)

    parser = get_parser(language)
    funcs = parser.extract_func_from_repo(repo_path)
    serializable = []
    for func in funcs:
        serializable.append(
            {
                "name": func.get("name", ""),
                "body": func.get("body", ""),
                "func": func.get("func", parser.nodetostr(func.get("func_node"))),
                "doc": func.get("doc", ""),
                "file_path": func.get("file_path", ""),
            }
        )
    write_json(path, serializable)
    return serializable


def splitter_prompt(func: dict[str, Any]) -> str:
    return f"""Write comment and doc string for the given code snippet.
** DO NOT write comment line by line, you should add a comment at a sub-module's begining.**.
A submodule refers to a code block or multiple lines of code that are highly semantically coherent and independently accomplish a key sub-function within a function.
Return the code snippet with comments and doc string.

Here is the code snippet you need to comment:
```
{func["func"]}
```
"""


def split_documents(
    functions: list[dict[str, Any]],
    language: str,
    splitter_cfg: dict[str, Any],
    cache_dir: Path,
    force: bool = False,
) -> list[dict[str, Any]]:
    path = cache_dir / "split_docs.json"
    if path.exists() and not force:
        return read_json(path)

    from rag.splitter import split_func

    docs: list[dict[str, Any]] = []
    system = "You are the CICO splitter model."
    for idx, func in enumerate(tqdm(functions, desc="Splitting functions")):
        response = chat_completion(splitter_cfg, system, splitter_prompt(func))
        commented_code = extract_code_blocks(response) or response
        func_data = {"func_str": func["func"], "commented_code": commented_code}
        try:
            pairs = split_func(func_data, language) or [(func["func"], func["func"])]
        except Exception:
            pairs = [(func["func"], func["func"])]

        for chunk_idx, pair in enumerate(pairs):
            key, value = pair[0], pair[1]
            docs.append(
                {
                    "id": f"{idx}:{chunk_idx}",
                    "key": key,
                    "value": value,
                    "meta": {
                        "language": language,
                        "file_path": func.get("file_path", ""),
                        "function_name": func.get("name", ""),
                    },
                }
            )

    write_json(path, docs)
    return docs


def build_index(
    docs: list[dict[str, Any]],
    embedding_cfg: dict[str, Any],
    cache_dir: Path,
    force: bool = False,
) -> Path:
    import faiss

    index_path = cache_dir / "index.faiss"
    docs_path = cache_dir / "index.faiss.json"
    if index_path.exists() and docs_path.exists() and not force:
        return index_path

    dimension = int(embedding_cfg.get("dimension", 4096))
    batch_size = int(embedding_cfg.get("batch_size", 8))
    index = faiss.IndexFlatL2(dimension)
    vectors = []
    for start in tqdm(range(0, len(docs), batch_size), desc="Embedding chunks"):
        batch = docs[start : start + batch_size]
        vectors.extend(embeddings(embedding_cfg, [doc["key"] for doc in batch]))

    arr = np.asarray(vectors, dtype="float32")
    if arr.shape[1] != dimension:
        raise ValueError(f"Embedding dimension mismatch: config={dimension}, actual={arr.shape[1]}")

    index.add(arr)
    cache_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    write_json(docs_path, docs)
    return index_path


def parse_planner_output(text: str) -> list[str]:
    payload = extract_code_blocks(text) or text
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return [line.strip("- ").strip() for line in payload.splitlines() if line.strip()]
    if isinstance(data, list):
        return [str(item) for item in data if str(item).strip()]
    if isinstance(data, dict):
        for key in ("plans", "comments", "queries", "subqueries"):
            if isinstance(data.get(key), list):
                return [str(item) for item in data[key] if str(item).strip()]
    return [payload.strip()] if payload.strip() else []


def plan_query(
    query: str,
    planner_cfg: dict[str, Any],
    prompts_cfg: dict[str, Any],
    q_cache_dir: Path,
    force: bool = False,
) -> list[str]:
    path = q_cache_dir / "plan.json"
    if path.exists() and not force:
        return read_json(path)["plans"]

    system = prompts_cfg["planner_system"]
    user = f"Query:\n{query}\n\nReturn only a JSON list of submodule comments or retrieval intents."
    response = chat_completion(planner_cfg, system, user)
    plans = parse_planner_output(response)
    if query not in plans:
        plans.insert(0, query)
    write_json(path, {"query": query, "raw_response": response, "plans": plans})
    return plans


def retrieve(
    plans: list[str],
    embedding_cfg: dict[str, Any],
    cache_dir: Path,
    q_cache_dir: Path,
    top_k_per_plan: int,
    final_top_k: int,
    force: bool = False,
) -> list[dict[str, Any]]:
    import faiss

    path = q_cache_dir / "retrieval.json"
    if path.exists() and not force:
        return read_json(path)

    index = faiss.read_index(str(cache_dir / "index.faiss"))
    docs = read_json(cache_dir / "index.faiss.json")
    seen: dict[str, dict[str, Any]] = {}

    for plan in plans:
        vector = np.asarray(embeddings(embedding_cfg, [plan]), dtype="float32")
        distances, indices = index.search(vector, top_k_per_plan)
        for distance, doc_idx in zip(distances[0], indices[0]):
            if doc_idx < 0:
                continue
            doc = docs[int(doc_idx)]
            key = stable_hash(doc["value"] + doc["meta"].get("file_path", ""))
            item = {
                "score": float(distance),
                "plan": plan,
                "value": doc["value"],
                "key": doc["key"],
                "meta": doc["meta"],
            }
            if key not in seen or item["score"] < seen[key]["score"]:
                seen[key] = item

    results = sorted(seen.values(), key=lambda item: item["score"])[:final_top_k]
    write_json(path, results)
    return results


def build_context(retrieved: list[dict[str, Any]], max_chars: int) -> str:
    chunks = []
    used = 0
    for idx, item in enumerate(retrieved, start=1):
        meta = item["meta"]
        header = f"[{idx}] {meta.get('file_path', '')}::{meta.get('function_name', '')}\n"
        body = item["value"].strip()
        chunk = header + body
        if used + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        used += len(chunk)
    return "\n\n".join(chunks)


def generate_answer(
    query: str,
    retrieved: list[dict[str, Any]],
    generator_cfg: dict[str, Any],
    prompts_cfg: dict[str, Any],
    max_context_chars: int,
    q_cache_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    path = q_cache_dir / "answer.json"
    if path.exists() and not force:
        return read_json(path)

    context = build_context(retrieved, max_context_chars)
    user = f"Repository context:\n{context}\n\nUser query:\n{query}"
    answer = chat_completion(generator_cfg, prompts_cfg["generator_system"], user)
    payload = {"query": query, "answer": answer, "context_items": len(retrieved)}
    write_json(path, payload)
    return payload


def run_pipeline(
    repo_path: str,
    query: str,
    language: str,
    config: dict[str, Any],
    force_rebuild: bool = False,
    stage: str = "generate",
) -> dict[str, Any]:
    pipeline_cfg = config["pipeline"]
    force = force_rebuild or bool(pipeline_cfg.get("force_rebuild", False))
    cache_dir = repo_cache_dir(pipeline_cfg["cache_dir"], repo_path, language)
    q_cache = query_cache_dir(cache_dir, query)
    q_cache.mkdir(parents=True, exist_ok=True)

    functions = parse_repo(repo_path, language, cache_dir, force)
    docs = split_documents(functions, language, config["models"]["splitter"], cache_dir, force)
    build_index(docs, config["models"]["embedding"], cache_dir, force)
    if stage == "index":
        return {
            "cache_dir": str(cache_dir),
            "query_cache_dir": str(q_cache),
            "function_count": len(functions),
            "chunk_count": len(docs),
            "plans": [],
            "retrieved_count": 0,
            "answer": "",
        }

    plans = plan_query(query, config["models"]["planner"], config["prompts"], q_cache, force=False)
    if stage == "plan":
        return {
            "cache_dir": str(cache_dir),
            "query_cache_dir": str(q_cache),
            "function_count": len(functions),
            "chunk_count": len(docs),
            "plans": plans,
            "retrieved_count": 0,
            "answer": "",
        }

    retrieved = retrieve(
        plans,
        config["models"]["embedding"],
        cache_dir,
        q_cache,
        int(pipeline_cfg.get("retrieve_top_k_per_plan", 3)),
        int(pipeline_cfg.get("retrieve_final_top_k", 8)),
        force=False,
    )
    if stage == "retrieve":
        return {
            "cache_dir": str(cache_dir),
            "query_cache_dir": str(q_cache),
            "function_count": len(functions),
            "chunk_count": len(docs),
            "plans": plans,
            "retrieved_count": len(retrieved),
            "answer": "",
        }

    answer = generate_answer(
        query,
        retrieved,
        config["models"]["generator"],
        config["prompts"],
        int(pipeline_cfg.get("max_context_chars", 16000)),
        q_cache,
        force=False,
    )
    return {
        "cache_dir": str(cache_dir),
        "query_cache_dir": str(q_cache),
        "function_count": len(functions),
        "chunk_count": len(docs),
        "plans": plans,
        "retrieved_count": len(retrieved),
        "answer": answer["answer"],
    }
