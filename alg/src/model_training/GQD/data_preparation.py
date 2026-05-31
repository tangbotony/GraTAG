import json
import argparse
from typing import List, Dict
from pathlib import Path


def prepare_sft_dataset(input_file: str, output_file: str, max_samples: int = None):
    print(f"Loading data from {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prepared_data = []
    
    for i, item in enumerate(data):
        if max_samples and i >= max_samples:
            break
        if 'query' not in item or 'decomposition' not in item:
            print(f"Warning: Skipping item {i}")
            continue
        prepared_data.append({
            'query': item['query'],
            'decomposition': item['decomposition'],
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in prepared_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"Saved {len(prepared_data)} samples to {output_file}")


def prepare_grpo_dataset(input_file: str, output_file: str, max_samples: int = None):
    print(f"Loading data from {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prepared_data = []
    
    for i, item in enumerate(data):
        if max_samples and i >= max_samples:
            break
        if 'query' not in item or 'answer' not in item:
            print(f"Warning: Skipping item {i}")
            continue
        prepared_item = {'query': item['query'], 'answer': item['answer']}
        if 'context' in item:
            prepared_item['context'] = item['context']
        if 'domain' in item:
            prepared_item['domain'] = item['domain']
        prepared_data.append(prepared_item)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in prepared_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"Saved {len(prepared_data)} samples to {output_file}")


def validate_dataset(dataset_file: str, dataset_type: str = "sft"):
    print(f"Validating {dataset_type} dataset: {dataset_file}")
    
    with open(dataset_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    errors = []
    
    for i, line in enumerate(lines):
        try:
            item = json.loads(line)
            
            if dataset_type == "sft":
                if 'query' not in item:
                    errors.append(f"Line {i+1}: Missing 'query'")
                if 'decomposition' not in item:
                    errors.append(f"Line {i+1}: Missing 'decomposition'")
            elif dataset_type == "grpo":
                if 'query' not in item:
                    errors.append(f"Line {i+1}: Missing 'query'")
                if 'answer' not in item:
                    errors.append(f"Line {i+1}: Missing 'answer'")
        
        except json.JSONDecodeError as e:
            errors.append(f"Line {i+1}: JSON decode error - {e}")
    
    if errors:
        print(f"Found {len(errors)} errors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... {len(errors) - 10} more")
    else:
        print(f"Dataset is valid! ({len(lines)} samples)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", type=str, required=True, choices=["prepare_sft", "prepare_grpo", "validate"])
    parser.add_argument("--input_file", type=str)
    parser.add_argument("--output_file", type=str)
    parser.add_argument("--max_samples", type=int)
    parser.add_argument("--dataset_type", type=str, default="sft", choices=["sft", "grpo"])
    
    args = parser.parse_args()
    
    if args.action == "prepare_sft":
        if not args.input_file or not args.output_file:
            print("Error: --input_file and --output_file required")
            return
        prepare_sft_dataset(args.input_file, args.output_file, args.max_samples)
    elif args.action == "prepare_grpo":
        if not args.input_file or not args.output_file:
            print("Error: --input_file and --output_file required")
            return
        prepare_grpo_dataset(args.input_file, args.output_file, args.max_samples)
    elif args.action == "validate":
        if not args.input_file:
            print("Error: --input_file required")
            return
        validate_dataset(args.input_file, args.dataset_type)


if __name__ == "__main__":
    main()

