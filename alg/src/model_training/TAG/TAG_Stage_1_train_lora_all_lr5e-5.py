import os
import subprocess

def train_model():
    CUDA_VISIBLE_DEVICES = "4"
    model_name_or_path = "xx"
    dataset = "pubmedqa,covidqa,hotpotqa,qmsum,govreport,cuad,news"
    dataset_dir = "./data"
    template = "qwen"
    finetuning_type = "lora"
    output_dir = "xx"
    cutoff_len = 20480
    preprocessing_num_workers = 16
    per_device_train_batch_size = 1
    per_device_eval_batch_size = 1
    gradient_accumulation_steps = 8
    lr_scheduler_type = "cosine"
    logging_steps = 50
    warmup_steps = 20
    save_steps = 100
    eval_steps = 50
    evaluation_strategy = "steps"
    load_best_model_at_end = True
    learning_rate = 5e-5
    num_train_epochs = 5.0
    max_samples = 1000
    val_size = 0.1
    plot_loss = True
    fp16 = True

    train_command = f"""
    CUDA_VISIBLE_DEVICES={CUDA_VISIBLE_DEVICES} llamafactory-cli train \
        --stage sft \
        --do_train \
        --model_name_or_path {model_name_or_path} \
        --dataset {dataset} \
        --dataset_dir {dataset_dir} \
        --template {template} \
        --finetuning_type {finetuning_type} \
        --output_dir {output_dir} \
        --overwrite_cache \
        --overwrite_output_dir \
        --cutoff_len {cutoff_len} \
        --preprocessing_num_workers {preprocessing_num_workers} \
        --per_device_train_batch_size {per_device_train_batch_size} \
        --per_device_eval_batch_size {per_device_eval_batch_size} \
        --gradient_accumulation_steps {gradient_accumulation_steps} \
        --lr_scheduler_type {lr_scheduler_type} \
        --logging_steps {logging_steps} \
        --warmup_steps {warmup_steps} \
        --save_steps {save_steps} \
        --eval_steps {eval_steps} \
        --evaluation_strategy {evaluation_strategy} \
        --load_best_model_at_end {str(load_best_model_at_end).lower()} \
        --learning_rate {learning_rate} \
        --num_train_epochs {num_train_epochs} \
        --max_samples {max_samples} \
        --val_size {val_size} \
        --plot_loss {str(plot_loss).lower()} \
        --fp16 {str(fp16).lower()}
    """

    print("Starting training...")
    subprocess.run(train_command, shell=True)

if __name__ == "__main__":
    train_model()