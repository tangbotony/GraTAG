# GQD: Graph-Based Query Decomposition Training

This directory contains the training code for GQD (Graph-Based Query Decomposition) using GRPO (Group Relative Policy Optimization).

## Overview

GQD trains Qwen2.5-72B-Instruct to decompose complex queries into graph-structured subqueries. The training consists of two stages:

1. **Stage 0: Cold Start with GPT-4** - Use GPT-4 to generate annotated GQD decomposition data
2. **Stage 1: Supervised Fine-Tuning (SFT)** - Train Qwen2.5 to learn GQD format using GPT-4 generated data
3. **Stage 2: GRPO** - Optimize Qwen2.5 using group-relative policy optimization

## Algorithm

### Stage 0: Cold Start with GPT-4

Use GPT-4 to generate training data with graph-structured query decompositions in JSON format:
```json
{
  "is_complex": true,
  "sub_queries": ["subquery1", "subquery2"],
  "parent_child": [{"parent": "subquery1", "child": "subquery2"}]
}
```

### Stage 1: SFT

Train Qwen2.5-72B-Instruct on GPT-4 generated data to learn:
- JSON output format for GQD
- Basic decomposition patterns
- Dependency structures between subqueries

### Stage 2: GRPO

Optimize Qwen2.5-72B-Instruct using:
- **Group Relative Advantages**: Normalize rewards within each batch
- **KL Constraint**: Keep policy close to reference model (snapshot from Stage 1)
- **PPO Clipping**: Stable policy updates

The algorithm samples K decompositions per query, executes retrieval and generation using the same Qwen2.5-72B-Instruct model, and optimizes based on answer quality.

## Files

- `GQD_Stage_1_SFT.py` - Stage 1 training
- `GQD_Stage_2_GRPO.py` - Stage 2 GRPO training  
- `retrieval.py` - Web retrieval module
- `utils.py` - Utility functions
- `prompt.py` - Prompts
- `constants.py` - Constants
- `data_preparation.py` - Data prep utils

## Data Format

### Stage 1 Dataset (SFT)

JSONL format with GPT-4 generated decompositions:

```json
{
  "query": "What were the main causes and consequences of World War II?",
  "decomposition": "{'is_complex': True, 'sub_queries': ['What were the main causes of World War II?', 'What were the main consequences of World War II?'], 'parent_child': []}"
}
```

### Stage 2 Dataset (GRPO)

JSONL format with queries and ground truth answers:

```json
{
  "query": "What were the main causes and consequences of World War II?",
  "answer": "World War II was caused by..."
}
```

## Usage

### Stage 1: SFT Training

```bash
python GQD_Stage_1_SFT.py \
    --model_path Qwen/Qwen2.5-72B-Instruct \
    --dataset_path /path/to/sft/dataset.jsonl \
    --output_dir ./outputs/stage1 \
    --model_type qwen \
    --lr 5e-5 \
    --batch_size 4 \
    --gradient_accumulation_steps 8 \
    --num_epochs 3 \
    --max_seq_length 2048 \
    --use_lora \
    --lora_r 16 \
    --lora_alpha 32
```

**Key Arguments:**
- `--model_path`: Path to Qwen2.5-72B-Instruct model
- `--dataset_path`: Path to GPT-4 generated SFT dataset (JSONL)
- `--model_type`: Use "qwen" for Qwen2.5-72B-Instruct
- `--use_lora`: Enable LoRA for efficient fine-tuning
- `--lora_r`: LoRA rank (default: 16)
- `--max_seq_length`: Maximum sequence length (default: 2048)

### Stage 2: GRPO Training

```bash
python GQD_Stage_2_GRPO.py \
    --model_path ./outputs/stage1/final_model \
    --dataset_path /path/to/grpo/dataset.jsonl \
    --output_dir ./outputs/stage2 \
    --lr 5e-7 \
    --batch_size 1 \
    --K_samples 4 \
    --beta_kl 0.01 \
    --epsilon_clip 0.2 \
    --temperature 0.7 \
    --top_p 0.9
```

**Key Arguments:**
- `--model_path`: Path to SFT model from Stage 1 (Qwen2.5-72B-Instruct)
- `--dataset_path`: Path to GRPO dataset with QA pairs (JSONL)
- `--K_samples`: Number of GQD samples per query (default: 4)
- `--beta_kl`: KL divergence coefficient (default: 0.01)
- `--epsilon_clip`: PPO clipping parameter (default: 0.2)
- `--temperature`: Sampling temperature (default: 0.7)

Note: Qwen2.5-72B-Instruct is used for decomposition, answer generation, and as reference model (snapshot at training start)

## Configuration

Edit `constants.py` to configure:

```python
MODEL_PATH = "Qwen/Qwen2.5-72B-Instruct"
DATASET_PATH = "/path/to/datasets/"

# Training hyperparameters
DEFAULT_LEARNING_RATE_SFT = 5e-5
DEFAULT_LEARNING_RATE_GRPO = 5e-7
DEFAULT_K_SAMPLES = 4
DEFAULT_BETA_KL = 0.01
DEFAULT_EPSILON_CLIP = 0.2

# Retrieval configuration
BOCHA_API_KEY = "sk-********"  # Bocha API key
OPENAI_API_KEY = "your_openai_api_key"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
SIMILARITY_THRESHOLD = 0.5
```

Or set as environment variables:
```bash
export BOCHA_API_KEY="sk-********"
export OPENAI_API_KEY="your_openai_api_key"
```

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Key deps: torch, transformers, trl, peft, datasets, wandb, openai, requests, beautifulsoup4, langchain

## Implementation Notes

### Retrieval System

The retrieval system (`retrieval.py`) implements:
1. **Bocha Search API** (https://api.bochaai.com) for web search
2. **Web scraping** with BeautifulSoup for content extraction
3. **LangChain** text splitter for chunking (500 chars with 100 overlap)
4. **Batch OpenAI Embeddings** (text-embedding-ada-002) for efficient parallel processing
5. **Vectorized cosine similarity** filtering with threshold > 0.5 using NumPy

Optimizations:
- Batch embedding (100 texts/request)
- Vectorized similarity via matrix ops
- Much faster than sequential

**Setup:**
```bash
# Set API keys in constants.py or environment
export BOCHA_API_KEY="sk-********"
export OPENAI_API_KEY="your_openai_api_key"
```

**Usage:**
```python
from retrieval import retrieve_documents

# Returns list of relevant text chunks
chunks = retrieve_documents("气候变化是什么？")
```

Get API key from [Bocha AI](https://www.bochaai.com/)

### Model Usage

Qwen2.5-72B-Instruct is used for all tasks:
1. **Decomposition**: Generate GQD structures
2. **Answer Generation**: Generate answers given query and evidence
3. **Reference Model**: A frozen snapshot for KL divergence computation

The reference model is automatically created from the current model at the start of GRPO training.

## Monitoring

Training progress is logged to Weights & Biases:
- Loss curves
- Advantage statistics
- Sample quality metrics
- KL divergence

Disable with `--debug` flag for local testing.

## Tips

1. **GPT-4 Data Generation**: Use GPT-4 with the provided prompt to generate high-quality decomposition data
2. **Bocha API**: Get your API key from [Bocha AI](https://www.bochaai.com/)
3. **Start Small**: Use `--debug` for initial testing
4. **Tune K**: More samples (K=4-8) improves exploration but increases compute
5. **KL Coefficient**: Increase `--beta_kl` if policy diverges too much from reference
6. **Clipping**: Adjust `--epsilon_clip` for more/less aggressive updates
7. **LoRA for Stage 1**: Use LoRA to reduce memory and speed up SFT (recommended for 72B model)
8. **Model**: Only Qwen2.5-72B-Instruct is used for all components


