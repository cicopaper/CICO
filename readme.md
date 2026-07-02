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
-- docs/
    -- cico_pipeline.md  # full pipeline reproduction steps
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

See `docs/cico_pipeline.md` for the staged cache layout and step-by-step pipeline.
