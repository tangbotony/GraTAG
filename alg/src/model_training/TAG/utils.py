import time
import numpy as np
import torch
import random
from transformers import AutoTokenizer
from trl import SFTTrainer
from torch.nn import DataParallel
import torch.nn.functional as F
import torch.distributed as dist
from constants import *

MODEL_PATH = ""
initial_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
initial_tokenizer.padding_side = "right"
initial_tokenizer.pad_token_id = initial_tokenizer.eos_token_id
answer_marker = '\nA: '
eval_answer_marker = "\nA:"

PROMPT_DICT = {
    "prompt_input": (
        "Below is an instruction that describes a task, paired with an input that provides further context. "
        "Write a response that appropriately completes the request.\n\n"
        "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n"
    ),
    "prompt_no_input": (
        "Below is an instruction that describes a task. "
        "Write a response that appropriately completes the request.\n\n"
        "### Instruction:\n{instruction}\n\n### Response:\n"
    )
}

MISTRAL_PROMPT = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
%s

### Response:
"""

LLAMA_PROMPT = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful AI assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>

%s<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

QWEN_PROMPT = """<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
%s<|im_end|>
<|im_start|>assistant
"""

def formatting_prompts_func_with_no_responses(examples):
    formatted_prompts = []
    for i in range(len(examples["instruction"])):
        instruction = examples["instruction"][i]
        input_text = examples["input"][i]
        if len(input_text) >= 2:
            text = PROMPT_DICT["prompt_input"].format(instruction=instruction, input=input_text)
        else:
            text = PROMPT_DICT["prompt_no_input"].format(instruction=instruction)
        formatted_prompts.append(text)
    return {"formatted_prompt": formatted_prompts}

def formatting_prompts_func(examples):
    output_text = []
    for i in range(len(examples["instruction"])):
        instruction = examples["instruction"][i]
        response = examples["output"][i]
        if "input" in examples and examples["input"][i] != "":
            input_text = examples["input"][i]
            text = PROMPT_DICT["prompt_input"].format(instruction=instruction, input=input_text) + response
        else:
            text = PROMPT_DICT["prompt_no_input"].format(instruction=instruction) + response
        output_text.append(text)
    return output_text

def formatting_prompts_func_llama(examples):
    output_text = []
    for i in range(len(examples["instruction"])):
        instruction = examples["instruction"][i]
        response = examples["output"][i]
        text = LLAMA_PROMPT % (instruction) + response
        output_text.append(text)
    print(output_text[:5])
    return output_text

def formatting_prompts_func_qwen(examples):
    output_text = []
    for i in range(len(examples["instruction"])):
        instruction = examples["instruction"][i]
        response = examples["output"][i]
        text = QWEN_PROMPT % (instruction) + response
        output_text.append(text)
    print(output_text[:5])
    return output_text

def formatting_prompts_func_with_thought(examples, prompt):
    output_text = []
    thought_format = "<|startextraction|>{}<|endextraction|>"
    for i in range(len(examples["instruction"])):
        instruction = examples["instruction"][i]
        thought = examples["thought"][i]
        response = examples["output"][i]
        text = prompt % (instruction) + thought_format.format(thought) + response
        output_text.append(text)
    print(output_text[:5])
    return output_text

def formatting_prompts_func_with_thought_mistral(examples):
    return formatting_prompts_func_with_thought(examples=examples, prompt=MISTRAL_PROMPT)

def formatting_prompts_func_with_thought_llama(examples):
    return formatting_prompts_func_with_thought(examples=examples, prompt=LLAMA_PROMPT)

def formatting_prompts_func_with_thought_qwen(examples):
    return formatting_prompts_func_with_thought(examples=examples, prompt=QWEN_PROMPT)

class CoTSFTTrainer(SFTTrainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def none_repeat_interleave(self, x, n):
        if x is None:
            return x
        return x.repeat_interleave(n, dim=0)

    def insert_elements(self, tensor, insert_elements, insert_positions):
        result_list = []
        start_id = self.tokenizer.convert_tokens_to_ids("<|startextraction|>")
        end_id = self.tokenizer.convert_tokens_to_ids("<|endextraction|>")
        lens = []
        for i in range(tensor.shape[0]):
            row = tensor[i]
            if insert_elements[i, -1] == self.tokenizer.pad_token_id:
                first_pad_idx = (insert_elements[i] == self.tokenizer.pad_token_id).nonzero(as_tuple=True)[0][0]
            else:
                first_pad_idx = None
            insert_ones = torch.cat((torch.tensor([start_id], device=tensor.device),insert_elements[i, :first_pad_idx],torch.tensor([end_id], device=tensor.device)))
            new_row = torch.cat((row[:insert_positions[i]], insert_ones, row[insert_positions[i]:]))
            result_list.append(new_row)
            lens.append(len(new_row))
        for i in range(len(result_list)):
            if len(result_list[i]) < max(lens):
                result_list[i] = torch.cat((result_list[i], torch.full((max(lens) - len(result_list[i]),), self.tokenizer.pad_token_id, device=tensor.device)), dim=0)
        return torch.stack(result_list)
    
    @torch.no_grad()
    def generate_cot_prompt_direct(self, model, inputs):
        if hasattr(model, "module"):
            real_model = model.module
        else:
            real_model = model
        
        input_ids = inputs.data["input_ids"]
        attention_mask = inputs.data["attention_mask"]
        labels = inputs.data["labels"]

        if real_model.n_passes > 1:
            input_ids = self.none_repeat_interleave(input_ids, real_model.n_passes)
            attention_mask = self.none_repeat_interleave(attention_mask, real_model.n_passes)
            labels = self.none_repeat_interleave(labels, real_model.n_passes)
        
        first_idx = (labels == -100).sum(dim=-1)
        new_input_ids = torch.full((input_ids.shape[0], max(first_idx) + real_model.n_ahead + 2), real_model.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)
        finished_generating = torch.zeros(len(input_ids), dtype=torch.bool, device=input_ids.device)
        new_attention_mask = torch.ones_like(new_input_ids)
        sampled_ids = torch.full((len(new_input_ids), real_model.n_ahead + 2), real_model.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)

        for i in range(len(first_idx)):
            new_input_ids[i, :first_idx[i]] = input_ids[i, :first_idx[i]]
            new_input_ids[i, first_idx[i]] = real_model.tokenizer.convert_tokens_to_ids("<|startoftext|>")

        sampled_ids[:, 0] = real_model.tokenizer.convert_tokens_to_ids("<|startoftext|>")
        sampled_ids[:, -1] = real_model.tokenizer.convert_tokens_to_ids("<|endoftext|>")
        for i in range(real_model.n_ahead):
            logits = model(new_input_ids[~finished_generating], attention_mask=new_attention_mask[~finished_generating])["logits"]
            logits[:, :, real_model.tokenizer.convert_tokens_to_ids("<|startextraction|>")] = -1e10
            logits[:, :, real_model.tokenizer.convert_tokens_to_ids("<|endextraction|>")] = -1e10
            probabilities = F.gumbel_softmax(logits, tau=real_model.gumbel_temperature, hard=True, dim=-1)
            new_ids = torch.argmax(probabilities, dim=-1) 
            for list_idx, answer_idx in enumerate((~finished_generating).nonzero(as_tuple=True)[0]):
                base_answer_ids = new_input_ids[answer_idx]
                last_token_idx = (base_answer_ids != model.tokenizer.pad_token_id).nonzero(as_tuple=True)[0].max()
                new_ids_sampled = new_ids[list_idx][last_token_idx]
                new_input_ids[answer_idx, last_token_idx + 1] = new_ids_sampled
                sampled_ids[answer_idx][i] = new_ids_sampled
                if new_ids_sampled in ((real_model.tokenizer.eos_token_id, real_model.end_token_id)):
                    new_input_ids[answer_idx, last_token_idx + 1] = real_model.end_token_id
                    finished_generating[answer_idx] = 1
            if finished_generating.all():
                break
        
        inputs.data["input_ids"] = input_ids
        inputs.data["attention_mask"] = attention_mask
        inputs.data["labels"] = labels
        return inputs, real_model.tokenizer.batch_decode(input_ids)
    
    @torch.no_grad()
    def generate_cot_prompt(self, model, inputs):
        model.eval()
        if hasattr(model, "module"):
            real_model = model.module
        else:
            real_model = model

        input_ids = inputs.data["input_ids"]
        attention_mask = inputs.data["attention_mask"]
        labels = inputs.data["labels"]

        if real_model.n_passes > 1:
            input_ids = self.none_repeat_interleave(input_ids, real_model.n_passes)
            attention_mask = self.none_repeat_interleave(attention_mask, real_model.n_passes)
            labels = self.none_repeat_interleave(labels, real_model.n_passes)
        
        input_strs = real_model.tokenizer.batch_decode(input_ids, skip_special_tokens=False)
        st_idx = [input_str.find(real_model.INSTRUCTION_MARK) + len(real_model.INSTRUCTION_MARK) for input_str in input_strs]
        ed_idx = [input_str.find(real_model.RESPONSE_MARK) for input_str in input_strs]
        instructions = [input_strs[i][st_idx[i]:ed_idx[i]].strip() for i in range(len(input_strs))]
        cot_prompts = [real_model.thought_prompt.format(instruction=instructions[i]) for i in range(len(instructions))]
        new_input = real_model.tokenizer(cot_prompts, return_tensors="pt", add_special_tokens=False, padding=True)
        new_input_ids = new_input["input_ids"].to(input_ids.device)
        finished_generating = torch.zeros(len(input_ids), dtype=torch.bool, device=input_ids.device)
        new_attention_mask = new_input["attention_mask"].to(input_ids.device)
        new_position_ids = torch.zeros(new_input_ids.shape[0], dtype=torch.long, device=input_ids.device)
        sampled_ids = torch.full((len(new_input_ids), real_model.n_ahead), real_model.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)
        
        if dist.is_initialized():
            signal = torch.zeros(1, dtype=torch.int32, device='cuda')
            world_size = dist.get_world_size()

        start_time = time.time()
        past_key_values = None
        for i in range(real_model.n_ahead):
            outputs = model(
                new_input_ids if past_key_values is None else sampled_ids[:, i - 1].unsqueeze(-1),
                attention_mask=new_attention_mask,
                use_cache=True,
                past_key_values=past_key_values,
                position_ids=new_position_ids.unsqueeze(-1) if past_key_values is not None else None,
            )
            logits = outputs["logits"]
            past_key_values = outputs.past_key_values
            logits[:, :, real_model.tokenizer.convert_tokens_to_ids("<|startthought|>")] = -1e10
            logits[:, :, real_model.tokenizer.convert_tokens_to_ids("<|endthought|>")] = -1e10
            probabilities = F.gumbel_softmax(logits, tau=real_model.gumbel_temperature, hard=False, dim=-1)
            new_padding = torch.full((len(new_input_ids), 1), real_model.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)
            new_input_ids = torch.cat([new_input_ids, new_padding], dim=-1)
            new_attention_mask = torch.cat([new_attention_mask, torch.ones_like(new_padding)], dim=-1)

            for list_idx, answer_idx in enumerate((~finished_generating).nonzero(as_tuple=True)[0]):
                new_ids = torch.multinomial(probabilities[answer_idx], num_samples=1).squeeze(-1)
                base_answer_ids = new_input_ids[answer_idx]
                last_token_idx = (base_answer_ids != real_model.tokenizer.pad_token_id).nonzero(as_tuple=True)[0].max()
                new_ids_sampled = new_ids[last_token_idx] if new_ids.shape[-1] != 1 else new_ids[0]
                new_input_ids[answer_idx, last_token_idx + 1] = new_ids_sampled
                sampled_ids[answer_idx][i] = new_ids_sampled
                new_position_ids[answer_idx] = last_token_idx + 1

                with open('log/CoT.txt', 'a') as f:
                    f.write(f"{model.tokenizer.decode(new_ids_sampled)}\n" + "="*40 + "\n")

                if new_ids_sampled in ((real_model.tokenizer.eos_token_id, real_model.end_token_id)):
                    new_input_ids[answer_idx, last_token_idx + 1] = real_model.end_token_id
                    finished_generating[answer_idx] = 1
            
            if finished_generating.all():
                if dist.is_initialized():
                    signal.fill_(1)
                else:
                    break
            if dist.is_initialized():
                signal_before = signal.item()
                dist.all_reduce(signal, op=dist.ReduceOp.SUM)
                if signal.item() == world_size:
                    break
                else:
                    signal.fill_(signal_before)
        
        end_time = time.time()
        print(f"run time: {end_time - start_time:.2f} 秒")
        first_idx = [(label != -100).nonzero(as_tuple=True)[0][0].item() for label in labels]
        input_ids = self.insert_elements(input_ids, sampled_ids, first_idx)
        attention_mask = torch.ones_like(input_ids)
        labels = input_ids.clone()
        for i in range(len(attention_mask)):
            labels[i, :first_idx[i]] = -100
            attention_mask[i] =  input_ids[i] != real_model.tokenizer.pad_token_id

        inputs.data["input_ids"] = input_ids
        inputs.data["attention_mask"] = attention_mask
        inputs.data["labels"] = labels
        print(self.tokenizer.batch_decode(input_ids))
        model.train()
        return inputs, real_model.tokenizer.batch_decode(input_ids)
        
    def training_step(self, model, inputs):
        new_inputs, sampled_thoughts = self.generate_cot_prompt(model, inputs)
        with open('./sampled_thoughts.txt', 'a') as f:
            for thought in sampled_thoughts:
                f.write(thought + '\n')
        return super().training_step(model, new_inputs)
