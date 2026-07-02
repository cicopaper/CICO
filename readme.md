# OFFICIAL REPO FOR PAPER: 
> Bridging the Granularity Gap: Achieving Semantic Alignment in Repository-Level Code Generation

## Repo Structure
```
-- data/                 # Datasets used in the paper
    -- *.xlsx            # test dataset for mrgbench
    -- *.json            # train data for cico's planner and splitter
-- parser/              # Code for parsing repositories into code functions using tree-sitter
-- rag/                 # code for rag pipeline in the paper
    -- embed_server.py  # script for running embedding server
    -- splitter.py      # split commented code into retrieval chunks
-- configs/
    -- cico_pipeline.yaml
                         # model paths, service endpoints, cache and retrieval config
-- cico_pipeline/        # staged CICO reproduction pipeline with caches
-- start_cico_services.py
                         # start/stop OpenAI-compatible services for the four models
-- mock_openai_server.py # lightweight mock services for dry-run pipeline checks
-- train_splitter_planner/
                         # optional training reproduction docs/configs for splitter and planner
-- utils/                # utility functions
-- readme.md           # this file
```

## Installation
There are 2 main environments used in CICO:
###  Training
For training the planner and splitter models, we use LLaMA-Factory as the training framework.
The organized training data, dataset registration template and training configs are under `train_splitter_planner/`.
See `train_splitter_planner/README.md` for the full training reproduction steps.

### Repo Parsing and Splitting
Once you have trained your model, or download our pre-trained model, you can start parsing a repository and run the CICO RAG pipeline. We recommend using a conda environment for this:
```bash
conda create -n cico python=3.10 -y
conda activate cico
pip install -r requirements.txt
```

If you need to serve splitter/planner/generator locally with vLLM on a Linux GPU machine, also install:
```bash
pip install -r requirements-vllm.txt
```

### Running CICO RAG Pipeline
The full CICO inference pipeline uses four models:

| Role | Default model |
| --- | --- |
| splitter | `cicopaper/cico-splitter` |
| planner | `cicopaper/cico-planner` |
| embedding | `Qwen/Qwen3-Embedding-8B` |
| generator | `Qwen/Qwen2.5-Coder-14B-Instruct` |

All model paths and OpenAI-compatible service endpoints are configured in `configs/cico_pipeline.yaml`.
The pipeline takes a `repo_path`, a `query`, and a language (`py`, `java`, or `go`).

If you only want to quickly verify that the environment and pipeline wiring are usable, run the dry-run mode first.
Dry-run mode starts lightweight mock OpenAI-compatible services and does not download large model weights.

```bash
python start_cico_services.py --config configs/cico_pipeline_dryrun.yaml --mock
python run_cico_pipeline.py \
  --config configs/cico_pipeline_dryrun.yaml \
  --repo-path /path/to/your/repo \
  --language py \
  --query "your task query" \
  --force-rebuild
python start_cico_services.py --config configs/cico_pipeline_dryrun.yaml --stop
```

In dry-run mode:

- embedding returns a deterministic bag-of-words hash embedding.
- planner splits the query into three roughly equal text chunks.
- splitter inserts a dry-run comment every two lines.
- generator returns a fixed `DRYRUN_GENERATION_OK` message.

Once you have installed the environment, configure the four model paths and endpoints in `configs/cico_pipeline.yaml`, then start the services and run the CICO pipeline:
```bash
# 1. start embedding, splitter, planner and generator services
python start_cico_services.py --config configs/cico_pipeline.yaml

# 2. run the full CICO reproduction pipeline
python run_cico_pipeline.py \
  --config configs/cico_pipeline.yaml \
  --repo-path /path/to/your/repo \
  --language py \
  --query "your task query"
```

The service helper can also print commands without starting them:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml --dry-run
```

Start only a subset of services:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml --models embedding,generator
```

Stop services started by the helper:

```bash
python start_cico_services.py --config configs/cico_pipeline.yaml --stop
```

Logs and pids are written to `.cico_services/`.

If splitter or planner checkpoints are LoRA adapters, export or merge them first with LLaMA-Factory, then set `model_name_or_path` to the exported model directory.

#### Cached Stages

Caches are stored under `.cico_cache/` by default. Each repository cache key is derived from the absolute repo path and language.

1. `functions.json`: parsed repository functions.
2. `split_docs.json`: splitter-produced query/document chunks.
3. `index.faiss` and `index.faiss.json`: FAISS embedding index and document payloads.
4. `plan.json`: planner output for each query.
5. `retrieval.json`: retrieved context for each query.
6. `answer.json`: generator response for each query.

Use `--force-rebuild` to rebuild parser/splitter/index caches for the repo.

#### Pipeline Steps

1. Parse repo: tree-sitter extracts functions/methods from the target repository. Test files are skipped by the parser.
2. Split documents: the splitter model adds docstrings/comments to functions and creates semantic chunks.
3. Embed and build index: `Qwen/Qwen3-Embedding-8B` embeds chunks through an OpenAI-compatible endpoint and FAISS stores the vector index.
4. Plan query: the planner decomposes the query into a JSON list of submodule comments or retrieval intents.
5. Retrieve context: each planned subquery is embedded and searched against FAISS, then results are deduplicated and reranked.
6. Generate answer: retrieved repository context and the original query are sent to the generator.

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
