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
    -- indexer.py       # index code and save to vector db
    -- splitter*.py     # split code into chunks for different languages
-- utils/                # utility functions
-- readme.md           # this file
```

## Installation
There are 2 main environments used in CICO:
###  Training
for training the planner and splitter models, we use LLaMA-FACTORY as our training framework. Please refer to [LLaMA-FACTORY](https://github.com/hiyouga/LLaMA-Factory/) for installation. Then copy `data/train/split.json` to `LLaMA-Factory/data/` for training the splitter model, and add the following dataset description to `LLaMA-Factory/data/dataset_info.json`:
```json
"split": {
    "file_name": "split.json",
    "columns": {
      "prompt": "instruction",
      "response": "output",
      "system": "system"
    }
  },
```
You can train your own splitter with any model supported by LLaMA-Factory now.

### Repo Parsing and Splitting
Once you have trained your model, or download our pre-trained model, you can start parsing a repository and run the CICO RAG pipeline. We recommend using a conda environment for this:
```bash
conda create -n cico python=3.10 -y
conda activate cico
pip install -r requirements.txt
```

### Running CICO RAG Pipeline
Once you have installed the environment, you can run the CICO RAG pipeline with the following command:
```bash
# 1. run the embedding server for indexing code
python rag/embed_server.py --model-path Qwen3/Qwen3-Embedding-8B
# 2. run the indexer to index code and save to vector db
python run_cico.py --repo-path /path/to/your/repo --mode full --language py
```