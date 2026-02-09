import argparse
import torch
import random
import os
import sys
import time
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
)
from datasets import load_dataset
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from constants import *
from utils import (
    formatting_prompts_func_mistral,
    formatting_prompts_func_llama,
    formatting_prompts_func_qwen,
)
from prompt import PROMPTS

random_seed = 42
torch.manual_seed(random_seed)
random.seed(random_seed)

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
parser.add_argument("--model_path", type=str, default=None)
parser.add_argument("--dataset_path", type=str, default=None)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--run_id", type=str, default=None)
parser.add_argument("--lr", type=float, default=DEFAULT_LEARNING_RATE_SFT)
parser.add_argument("--batch_size", type=int, default=DEFAULT_BATCH_SIZE)
parser.add_argument("--gradient_accumulation_steps", type=int, default=DEFAULT_GRADIENT_ACCUMULATION_STEPS)
parser.add_argument("--num_epochs", type=int, default=DEFAULT_NUM_TRAIN_EPOCHS)
parser.add_argument("--max_seq_length", type=int, default=DEFAULT_MAX_SEQ_LENGTH)
parser.add_argument("--model_type", type=str, default="mistral", choices=["mistral", "llama", "qwen"])
parser.add_argument("--use_lora", action="store_true")
parser.add_argument("--lora_r", type=int, default=16)
parser.add_argument("--lora_alpha", type=int, default=32)
parser.add_argument("--warmup_steps", type=int, default=100)
parser.add_argument("--save_steps", type=int, default=500)
parser.add_argument("--logging_steps", type=int, default=10)

args = parser.parse_args()

wandb_cache_dir = root_prefix + "cache/GQD/wandb_cache"
project_name = "GQD-SFT"
os.environ["WANDB_PROJECT"] = project_name
os.environ["WANDB_CACHE_DIR"] = wandb_cache_dir
if args.debug:
    os.environ["WANDB_DISABLED"] = "true"


def init_model_and_tokenizer():
    model_path = args.model_path if args.model_path else MODEL_PATH
    print(f"Loading model from: {model_path}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.padding_side = "right"
    tokenizer.pad_token_id = tokenizer.eos_token_id
    
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        cache_dir=root_prefix + "cache",
        device_map="auto" if torch.cuda.is_available() else None,
    )
    
    if args.use_lora:
        from peft import LoraConfig, get_peft_model
        lora_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
    
    print(f"Total parameters: {sum(p.numel() for p in model.parameters())}")
    print(f"Trainable: {sum(p.numel() for p in model.parameters() if p.requires_grad)}")
    
    return model, tokenizer


def get_formatting_func(model_type: str):
    if model_type == "mistral":
        return formatting_prompts_func_mistral
    elif model_type == "llama":
        return formatting_prompts_func_llama
    elif model_type == "qwen":
        return formatting_prompts_func_qwen
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def get_response_template(model_type: str):
    if model_type == "qwen":
        return "<|im_start|>assistant\n"
    elif model_type == "llama":
        return "<|start_header_id|>assistant<|end_header_id|>\n\n"
    else:
        return "### Response:\n"


def main():
    model, tokenizer = init_model_and_tokenizer()
    
    dataset_path = args.dataset_path if args.dataset_path else DATASET_PATH
    print(f"Loading dataset: {dataset_path}")
    
    try:
        dataset = load_dataset("json", data_files=dataset_path, download_mode="force_redownload")["train"]
        print(f"Loaded {len(dataset)} examples")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return
    
    formatting_func = get_formatting_func(args.model_type)
    response_template = get_response_template(args.model_type)
    collator = DataCollatorForCompletionOnlyLM(response_template, tokenizer=tokenizer)
    
    run_id = args.run_id if args.run_id else str(int(time.time()))
    output_dir = args.output_dir if args.output_dir else (root_prefix + f"cache/GQD/stage1_{run_id}")
    
    run_name = f"gqd_sft_lr{args.lr}_bs{args.batch_size}"
    if args.use_lora:
        run_name += f"_lora_r{args.lora_r}"
    if args.run_id:
        run_name += f"_{args.run_id}"
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=args.lr,
        optim="adamw_torch",
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_grad_norm=1.0,
        num_train_epochs=args.num_epochs,
        bf16=torch.cuda.is_available(),
        fp16=False,
        warmup_steps=args.warmup_steps,
        weight_decay=0.01,
        label_names=["labels"],
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        run_name=run_name,
        report_to="wandb" if not args.debug else "none",
        load_best_model_at_end=False,
    )
    
    trainer = SFTTrainer(
        args=training_args,
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        formatting_func=formatting_func,
        max_seq_length=args.max_seq_length,
        data_collator=collator,
        packing=False,
    )
    
    print(f"Starting training... Output: {output_dir}")
    trainer.train()
    
    final_model_path = os.path.join(output_dir, "final_model")
    trainer.save_model(final_model_path)
    
    print(f"Training complete! Model: {final_model_path}")


if __name__ == "__main__":
    main()

