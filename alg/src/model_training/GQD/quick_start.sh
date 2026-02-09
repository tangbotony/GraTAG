#!/bin/bash

set -e

BASE_MODEL="Qwen/Qwen2.5-72B-Instruct"
OUTPUT_BASE_DIR="./outputs"
DATA_DIR="./data"

echo "Starting GQD Training Pipeline..."
echo "Stage 1: SFT Training"
python GQD_Stage_1_SFT.py \
    --model_path ${BASE_MODEL} \
    --dataset_path ${DATA_DIR}/sft_data.jsonl \
    --output_dir ${OUTPUT_BASE_DIR}/stage1 \
    --model_type qwen \
    --lr 5e-5 \
    --batch_size 2 \
    --gradient_accumulation_steps 4 \
    --num_epochs 3 \
    --max_seq_length 2048 \
    --use_lora \
    --lora_r 16 \
    --lora_alpha 32 \
    --warmup_steps 50 \
    --save_steps 100 \
    --logging_steps 10

echo "SFT done. Model: ${OUTPUT_BASE_DIR}/stage1/final_model"
echo ""
echo "Stage 2: GRPO Training"
python GQD_Stage_2_GRPO.py \
    --model_path ${OUTPUT_BASE_DIR}/stage1/final_model \
    --dataset_path ${DATA_DIR}/grpo_data.jsonl \
    --output_dir ${OUTPUT_BASE_DIR}/stage2 \
    --lr 5e-7 \
    --batch_size 1 \
    --gradient_accumulation_steps 8 \
    --num_epochs 2 \
    --K_samples 4 \
    --beta_kl 0.01 \
    --epsilon_clip 0.2 \
    --temperature 0.7 \
    --top_p 0.9 \
    --save_steps 50 \
    --logging_steps 10

echo "Done! Final model: ${OUTPUT_BASE_DIR}/stage2/final_model"

