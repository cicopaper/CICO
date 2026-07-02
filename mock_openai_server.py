from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="CICO Mock OpenAI Server")

SERVICE_ROLE = "generic"
EMBED_DIM = 128


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model: str | None = None
    encoding_format: str | None = "float"
    user: str | None = None


class ChatRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = None
    max_tokens: int | None = None


def now() -> int:
    return int(time.time())


def extract_last_user(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def extract_code_block(text: str) -> str:
    match = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip("\n")
    return text


def detect_language(code: str) -> str:
    stripped = code.lstrip()
    if stripped.startswith("def ") or "\ndef " in code:
        return "python"
    if stripped.startswith("func ") or "\nfunc " in code:
        return "go"
    if "public " in code or "private " in code or "class " in code:
        return "java"
    return ""


def comment_for_language(language: str, index: int) -> str:
    if language == "python":
        return f"    # dryrun splitter chunk {index}"
    return f"    // dryrun splitter chunk {index}"


def mock_splitter(user: str) -> str:
    code = extract_code_block(user)
    language = detect_language(code)
    lines = code.splitlines()
    out = []
    comment_idx = 1
    for idx, line in enumerate(lines, start=1):
        out.append(line)
        if language == "python" and idx == 1 and line.lstrip().startswith("def "):
            indent = re.match(r"^(\s*)", line).group(1) + "    "
            out.append(f'{indent}"""dryrun splitter function docstring"""')
            continue
        if idx > 1 and (idx - 1) % 2 == 0:
            out.append(comment_for_language(language, comment_idx))
            comment_idx += 1
    fence = language or ""
    return f"```{fence}\n" + "\n".join(out) + "\n```"


def split_three(text: str) -> list[str]:
    words = text.split()
    if not words:
        return ["dryrun planner empty query"]
    size = max(1, math.ceil(len(words) / 3))
    chunks = [" ".join(words[i : i + size]) for i in range(0, len(words), size)]
    while len(chunks) < 3:
        chunks.append(chunks[-1])
    return chunks[:3]


def mock_planner(user: str) -> str:
    match = re.search(r"Query:\s*(.*?)\n\nReturn only", user, re.DOTALL)
    query = match.group(1).strip() if match else user.strip()
    return "```json\n" + json.dumps(split_three(query), ensure_ascii=False) + "\n```"


def mock_generator(user: str) -> str:
    context_items = len(re.findall(r"^\[\d+\]", user, flags=re.MULTILINE))
    return (
        "DRYRUN_GENERATION_OK\n"
        f"Retrieved context items: {context_items}\n"
        "This fixed response confirms parser, splitter, embedding, retrieval, planner, and generator wiring ran end to end."
    )


def mock_chat(role: str, user: str) -> str:
    if role == "splitter":
        return mock_splitter(user)
    if role == "planner":
        return mock_planner(user)
    if role == "generator":
        return mock_generator(user)
    return "DRYRUN_CHAT_OK"


def bow_embedding(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    tokens = re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\d+|[\u4e00-\u9fff]", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(item * item for item in vec)) or 1.0
    return [item / norm for item in vec]


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest) -> dict[str, Any]:
    texts = request.input if isinstance(request.input, list) else [request.input]
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": bow_embedding(str(text), EMBED_DIM), "index": idx}
            for idx, text in enumerate(texts)
        ],
        "model": request.model or f"dryrun-{SERVICE_ROLE}",
    }


@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatRequest) -> dict[str, Any]:
    user = extract_last_user(request.messages)
    content = mock_chat(SERVICE_ROLE, user)
    return {
        "id": f"chatcmpl-dryrun-{SERVICE_ROLE}",
        "object": "chat.completion",
        "created": now(),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def main() -> None:
    global SERVICE_ROLE, EMBED_DIM
    parser = argparse.ArgumentParser(description="Run a lightweight mock OpenAI-compatible service for CICO dry runs.")
    parser.add_argument("--role", choices=["embedding", "splitter", "planner", "generator", "generic"], default="generic")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--embedding-dim", type=int, default=128)
    args = parser.parse_args()
    SERVICE_ROLE = args.role
    EMBED_DIM = args.embedding_dim
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
