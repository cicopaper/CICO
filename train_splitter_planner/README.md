# Splitter and Planner Training Reproduction

This directory records the optional training path for reproducing the two CICO auxiliary models:

- `splitter`: learns document/code chunk splitting and comment-enhanced semantic alignment.
- `planner`: learns query/task decomposition before retrieval.

Training these two models is not required for running the released CICO pipeline. The official checkpoints can be downloaded directly once the Hugging Face links are published; see `published_models.md`.

## 1. Install LLaMA-Factory

Clone and install LLaMA-Factory outside this repository or in a sibling directory:

```bash
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
conda create -n llamafactory python=3.11 -y
conda activate llamafactory
pip install -e .
pip install -r requirements/metrics.txt
```

For multi-GPU or DeepSpeed training, install the extra DeepSpeed requirements in the LLaMA-Factory repository:

```bash
pip install -r requirements/deepspeed.txt
```

## 2. Download Base Models

The paper training uses Qwen2.5-Coder base models. Download or reference these model IDs in the YAML configs:

```text
Qwen/Qwen2.5-Coder-1.5B
Qwen/Qwen2.5-Coder-7B
```

If the model has already been downloaded locally, set `model_name_or_path` in the YAML file to the local model directory.

## 3. Register Datasets

The two training datasets are already organized under `train_splitter_planner/data/`:

```text
train_splitter_planner/data/cico_splitter.json
train_splitter_planner/data/cico_planner.json
```

Copy them into LLaMA-Factory's `data/` directory:

```bash
cp /path/to/CICO/train_splitter_planner/data/cico_splitter.json /path/to/LLaMA-Factory/data/cico_splitter.json
cp /path/to/CICO/train_splitter_planner/data/cico_planner.json /path/to/LLaMA-Factory/data/cico_planner.json
```

Both files use the Alpaca-style schema expected by LLaMA-Factory:

```json
[
  {
    "instruction": "training prompt",
    "system": "system prompt",
    "output": "model response"
  }
]
```

Append the entries in `dataset_info.cico.template.json` to LLaMA-Factory's `data/dataset_info.json`.

## 4. Start Training

From the LLaMA-Factory repository root, launch the selected config:

```bash
llamafactory-cli train /path/to/CICO/train_splitter_planner/configs/train_splitter_qwen25_coder_1_5b_lora.yaml
llamafactory-cli train /path/to/CICO/train_splitter_planner/configs/train_splitter_qwen25_coder_7b_lora.yaml
llamafactory-cli train /path/to/CICO/train_splitter_planner/configs/train_planner_qwen25_coder_1_5b_lora.yaml
llamafactory-cli train /path/to/CICO/train_splitter_planner/configs/train_planner_qwen25_coder_7b_lora.yaml
```

Each run writes checkpoints under:

```text
saves/cico_splitter/qwen25_coder_1_5b_lora
saves/cico_splitter/qwen25_coder_7b_lora
saves/cico_planner/qwen25_coder_1_5b_lora
saves/cico_planner/qwen25_coder_7b_lora
```

These checkpoints are the trained `splitter` and `planner` models used by the reproduction pipeline.

## 5. Use Published Models Instead

The training path above is optional. To skip training, download the published splitter and planner models from the Hugging Face links in `published_models.md`, then point the CICO runtime to those model paths.
