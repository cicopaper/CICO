# CICO Pipeline Reproduction

The full CICO inference pipeline uses four models:

| Role | Default model |
| --- | --- |
| splitter | CICO splitter checkpoint, trained or downloaded |
| planner | CICO planner checkpoint, trained or downloaded |
| embedding | Qwen/Qwen3-Embedding-8B |
| generator | Qwen/Qwen2.5-Coder-14B-Instruct |

All paths and OpenAI-compatible service endpoints are configured in `configs/cico_pipeline.yaml`.

The pipeline does not start model services automatically. Start them first with `start_cico_services.py`, or point the config to already-running OpenAI-compatible endpoints.

## Input

The pipeline takes:

- `repo_path`: repository to index.
- `query`: user task/query.
- `language`: one of `py`, `java`, `go`.

## Cached Stages

Caches are stored under `.cico_cache/` by default. Each repository cache key is derived from the absolute repo path and language.

1. `functions.json`: parsed repository functions.
2. `split_docs.json`: splitter-produced query/document chunks.
3. `index.faiss` and `index.faiss.json`: FAISS embedding index and document payloads.
4. `plan.json`: planner output for each query.
5. `retrieval.json`: retrieved context for each query.
6. `answer.json`: generator response for each query.

## Steps

### 0. Start Model Services

The repository provides a helper that reads `configs/cico_pipeline.yaml` and starts:

- embedding: `rag/embed_server.py`
- splitter: vLLM OpenAI-compatible chat server
- planner: vLLM OpenAI-compatible chat server
- generator: vLLM OpenAI-compatible chat server

Print the commands without starting them:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml --dry-run
```

Start all four services:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml
```

Start only a subset:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml --models embedding,generator
```

Logs and pids are written to `.cico_services/`:

```text
.cico_services/logs/embedding.log
.cico_services/logs/splitter.log
.cico_services/logs/planner.log
.cico_services/logs/generator.log
.cico_services/pids/*.pid
```

Stop services started by the helper:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml --stop
```

If splitter or planner checkpoints are LoRA adapters, export or merge them first with LLaMA-Factory, then set `model_name_or_path` to the exported model directory.

### 1. Parse Repo

Tree-sitter extracts functions/methods from the target repository. Test files are skipped by the existing parser logic.

### 2. Split Documents

The splitter model adds docstrings/comments to functions and creates semantic chunks. Each chunk is indexed with:

- `key`: text embedded for retrieval.
- `value`: original function/code context.
- `meta`: language, file path, function name, chunk type.

### 3. Embed and Build Index

`Qwen/Qwen3-Embedding-8B` embeds the split chunks through an OpenAI-compatible embedding endpoint. FAISS stores the vector index.

### 4. Plan Query

The planner model decomposes the input query into a JSON list of submodule comments or retrieval intents.

### 5. Retrieve Context

Each planned subquery is embedded and searched against the FAISS index. Results are deduplicated and reranked by vector distance.

### 6. Generate Answer

The retrieved repository context and original query are sent to `Qwen/Qwen2.5-Coder-14B-Instruct` through an OpenAI-compatible chat endpoint.

## Command

```bash
python run_cico_pipeline.py \
  --config configs/cico_pipeline.yaml \
  --repo-path /path/to/repo \
  --language py \
  --query "Implement ..."
```

Use `--force-rebuild` to rebuild parser/splitter/index caches for the repo.

## Dry Run Without Model Downloads

Use the dry-run config and mock services to validate the whole pipeline without downloading any model:

```bash
python start_cico_services.py --config configs/cico_pipeline_dryrun.yaml --mock
```

The mock services behave as follows:

- embedding: returns a deterministic bag-of-words hash embedding.
- planner: splits the query into three roughly equal text chunks.
- splitter: inserts a dry-run comment every two lines.
- generator: returns a fixed `DRYRUN_GENERATION_OK` message.

Then run:

```bash
python run_cico_pipeline.py \
  --config configs/cico_pipeline_dryrun.yaml \
  --repo-path /path/to/repo \
  --language py \
  --query "Implement a dry-run test" \
  --force-rebuild
```

Stop the mock services:

```bash
python start_cico_services.py --config configs/cico_pipeline_dryrun.yaml --stop
```

To run one stage at a time:

```bash
# Parse repo, run splitter, embed chunks, and build FAISS index.
python run_cico_pipeline.py --stage index --config configs/cico_pipeline.yaml --repo-path /path/to/repo --language py --query "placeholder"

# Plan the query. Reuses index cache if present.
python run_cico_pipeline.py --stage plan --config configs/cico_pipeline.yaml --repo-path /path/to/repo --language py --query "Implement ..."

# Retrieve context. Reuses index and plan cache if present.
python run_cico_pipeline.py --stage retrieve --config configs/cico_pipeline.yaml --repo-path /path/to/repo --language py --query "Implement ..."

# Generate final answer. Reuses all previous caches if present.
python run_cico_pipeline.py --stage generate --config configs/cico_pipeline.yaml --repo-path /path/to/repo --language py --query "Implement ..."
```
