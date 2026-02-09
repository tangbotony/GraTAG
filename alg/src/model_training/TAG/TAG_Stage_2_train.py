import argparse
import torch
torch.backends.cuda.matmul.allow_tf32 = True  
import random
from transformers import AutoTokenizer, AutoModelForCausalLM, Qwen2TokenizerFast
from datasets import load_dataset
from transformers import TrainingArguments, AdamW
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
import os
import time
from utils import *
from constants import *
from prompt import PROMPTS
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

random_seed = 42
torch.manual_seed(random_seed)  
random.seed(random_seed)  

argparse = argparse.ArgumentParser()
argparse.add_argument("--debug", action="store_true")  
argparse.add_argument("--sft", action="store_true")  
argparse.add_argument("--warmup", action="store_true")  
argparse.add_argument("--model_path", type=str, default=None)  
argparse.add_argument("--run_id", type=str, default=None)  
argparse.add_argument("--mixing_weight", type=float, default=-1)  
argparse.add_argument("--max_steps", type=int, default=-1)  
argparse.add_argument("--n_passes", type=int, default=None)  
argparse.add_argument("--n_ahead", type=int, default=None)  
argparse.add_argument("--lr", type=float, default=5e-7)  
argparse.add_argument("--original_loss_weight", type=float, default=0.5)  
argparse.add_argument("--domain", type=str, default=None)  
args = argparse.parse_args()  

wandb_cache_dir = root_prefix + "cache/TAG/wandb_cache"  
project_name = "TAG-rl"
os.environ["WANDB_PROJECT"] = project_name  
os.environ["WANDB_CACHE_DIR"] = wandb_cache_dir 
if args.debug:
    os.environ["WANDB_DISABLED"] = "true"  

n_passes_global = (3 if args.n_passes is None else args.n_passes) if not args.warmup else 1  
n_ahead_global = 200 if args.n_ahead is None else args.n_ahead  
full_batch_size = 1 if not args.warmup else 1  
eval_and_logging_steps = 1  
save_steps = 25000  
model_name = MODEL_PATH_PREFIX + "Mistral-7B-Instruct" if args.model_path is None else args.model_path  
batch_size = full_batch_size  
global_gradient_accumulation_steps = 1  

@torch.no_grad()  
def init():
    original = True
    n_ahead = n_ahead_global
    n_ahead_talk = 1
    n_passes = n_passes_global
    gumbel_temperature = 0.7
    use_start_thought_token = True
    use_end_thought_token = True
    include_policy_loss = True
    gumbel_detach = True
    merged_talk_heads = True
    gradient_accumulation_steps = global_gradient_accumulation_steps 
    residual_think_head = False
    optimize_lm_head_only_at_start = False

    print("Loading model")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32, 
        cache_dir=root_prefix + "cache",  
        max_thoughts=n_ahead + n_ahead_talk + 1,  
        merged_talk_heads=merged_talk_heads,  
        merged_lm_and_talk_heads=False,  
        merged_lm_and_think_heads=True,  
        use_concat_talk_head=True, 
        use_shallow_think=True,  
        use_shallow_talk=False,  
        use_complex_think_head=False,  
        use_complex_talk_head=True, 
        use_weighted_talk_head=True,  
        warmup = args.warmup, 
    )
    print("Loaded model")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name) 
    tokenizer.padding_side = "right"  
    tokenizer.pad_token_id = tokenizer.eos_token_id  

    special_tokens_to_add = []
    if use_start_thought_token:
        special_tokens_to_add.append("<|startextraction|>")  
    if use_end_thought_token:
        special_tokens_to_add.append("<|endextraction|>") 
    
    if special_tokens_to_add:
        tokenizer.add_special_tokens({"additional_special_tokens": special_tokens_to_add}) 
        model.resize_token_embeddings(len(tokenizer))  
    model.tokenizer = tokenizer  
    model.gumbel_detach = gumbel_detach  
    model.include_policy_loss = include_policy_loss  
    model.use_end_thought_token = use_end_thought_token  
    model.use_start_thought_token = use_start_thought_token  
    model.n_ahead = n_ahead  
    model.n_ahead_talk = n_ahead_talk  
    model.n_passes = n_passes  
    model.n_tokens_print = gradient_accumulation_steps
    model.gradient_accumulation_steps = gradient_accumulation_steps
    model.residual_think_head = residual_think_head
    model.optimize_lm_head_only_at_start = optimize_lm_head_only_at_start
    model.gumbel_temperature = gumbel_temperature
    model.wandb_enabled = True
    model.original_mode = original
    model.config_params = None
    model.run_start = int(time.time())
    model.kill_after = None
    model.use_quiet_star_sft = True
    model.original_loss_weight = args.original_loss_weight
    model.use_L2_loss = False
    
    model.start_token_id = tokenizer.convert_tokens_to_ids("<|startextraction|>")
    model.end_token_id = tokenizer.convert_tokens_to_ids("<|endextraction|>")
    if args.domain == "General":
        model.thought_prompt = PROMPTS["General_scale"]
    elif args.domain == "Bio":
        model.thought_prompt = PROMPTS["Bio"]
    elif args.domain == "Legal":
        model.thought_prompt = PROMPTS["Legal"]
    elif args.domain == "News":
        model.thought_prompt = PROMPTS["News"]

    if model.warmup:
        model.mixing_weight = 1.0
        model.fixed_weight = True
        model.original_loss_weight = 0.0
        model.policy_loss_beta = 1.0
        if model.start_token_id == 0:
            model.start_token_id = model.tokenizer.bos_token_id
            model.tokenizer_has_start_thought_token = False
        elif model.use_start_thought_token:
            base_start_id = model.tokenizer.encode(model.initial_start_token, add_special_tokens=False)[0]
            if not model.initialize_thought_embedding_to_normal:
                model.model.embed_tokens.weight.data[model.start_token_id] = model.model.embed_tokens.weight.data[base_start_id].clone().detach()
        if model.end_token_id == 0:
            model.end_token_id = model.tokenizer.eos_token_id
            model.tokenizer_has_end_thought_token = False
        elif model.use_end_thought_token:
            base_end_id = model.tokenizer.encode(model.initial_end_token, add_special_tokens=False)[0]
            if not model.initialize_thought_embedding_to_normal:
                model.model.embed_tokens.weight.data[model.end_token_id] = model.model.embed_tokens.weight.data[base_end_id].clone().detach()

        def grad_scaling_hook(grad):
            scale_mask = torch.ones_like(grad)
            scale_mask[model.start_token_id] = 1e5
            scale_mask[model.end_token_id] = 1e5
            return grad * scale_mask

        model.model.embed_tokens.weight.register_hook(grad_scaling_hook)
    
    if args.mixing_weight > 0:
        model.mixing_weight = args.mixing_weight
        model.fixed_weight = True
    
    model.train()
    
    return model, tokenizer

def main():
    run_id = int(time.time()) if args.run_id is None else (f"np_{n_passes_global}_nahead_{n_ahead_global}" + args.run_id)
    
    if args.warmup:
        dataset = load_dataset("json", data_files="",download_mode="force_redownload")["train"]
    elif args.debug:
        dataset = load_dataset("json", data_files="")["train"]
    else:
        dataset = load_dataset("json", data_files="", download_mode="force_redownload")["train"]

    model, tokenizer = init()
    if isinstance(tokenizer, Qwen2TokenizerFast):
        response_template = "<|im_start|>assistant\n"
        format_func = formatting_prompts_func_qwen
        format_func_with_thought = formatting_prompts_func_with_thought_qwen
    else:
        format_func = formatting_prompts_func
        format_func_with_thought = formatting_prompts_func_with_thought_mistral
        response_template = "Response:\n"
    collator = DataCollatorForCompletionOnlyLM(response_template, tokenizer=tokenizer)

    run_name = "warmup" if args.warmup else f"n_{n_ahead_global}_np_{n_passes_global}_lr_{args.lr}"
    if args.mixing_weight > 0:
        run_name += f"_m{args.mixing_weight}"
    if args.run_id is not None:
        run_name += f"-{args.run_id}"

    training_args = TrainingArguments(
        output_dir=root_prefix + f"cache/TAG/{run_id}",
        learning_rate=args.lr,
        optim="adamw_torch",
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=global_gradient_accumulation_steps,
        max_grad_norm=1.0,
        num_train_epochs=3,
        max_steps= args.max_steps if args.max_steps > 0 else -1,
        bf16=True,
        warmup_steps=20,
        weight_decay=0.001,
        label_names=["labels"],
        include_inputs_for_metrics=True,
        logging_steps=eval_and_logging_steps,
        save_steps=save_steps,
        run_name= run_name,
    )

    if args.sft or args.warmup :
        trainer = SFTTrainer(
            args=training_args,
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            formatting_func=format_func if not args.warmup else format_func_with_thought,
            max_seq_length=512,
            data_collator=collator,
            packing=False,
        )
    else:
        trainer = CoTSFTTrainer(
            args=training_args,
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            formatting_func=format_func,
            max_seq_length=1024,
            data_collator=collator,
            packing=False,
        )

    trainer.train()

if __name__ == "__main__":
    main()
