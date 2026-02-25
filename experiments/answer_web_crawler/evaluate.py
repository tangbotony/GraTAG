"""BrowseComp benchmark evaluation."""

import json
import os
import time
import csv
from collections import defaultdict
from gpt_client import chat_with_gpt


EXTRACT_ANSWER_PROMPT = """You are evaluating an AI search engine's response to a question from the BrowseComp benchmark.

The question requires a short, specific factual answer. Your task is to extract the final answer from the AI search engine's response.

**Question:**
{question}

**AI Search Engine's Response:**
{response}

**Instructions:**
1. Read the AI search engine's response carefully.
2. Extract the most relevant short answer that directly answers the question.
3. If the response does not contain a clear answer or says it cannot answer, output "NO_ANSWER".
4. Output ONLY the extracted answer, nothing else. Keep it as short and specific as possible (a name, number, date, etc.).
5. Do NOT add any explanation or reasoning - just the answer itself.

**Your extracted answer:**"""


JUDGE_ANSWER_PROMPT = """You are a strict and precise judge for the BrowseComp benchmark. Your task is to determine if the extracted answer matches the ground truth answer.

**Question:**
{question}

**Ground Truth Answer:**
{ground_truth}

**Extracted Answer from AI Search Engine:**
{extracted_answer}

**Strict Judging Rules:**
1. The extracted answer is CORRECT ONLY if it conveys the SAME factual information as the ground truth.
2. Minor variations in formatting, capitalization, abbreviations, or phrasing are acceptable (e.g., "St. John's Health Center" vs "Saint John's Health Center").
3. For numerical answers (years, dates, counts): the numbers MUST match. "1985-1986" does NOT match "1988-96". "3:50 PM" matches "3:50 PM" but not "3:30 PM".
4. For names: the core name must match. Minor spelling variations are OK, but different people/places are NOT.
5. Partial answers are INCORRECT - the answer must be complete.
6. If the extracted answer is "NO_ANSWER", empty, or clearly irrelevant, it is INCORRECT.
7. When in doubt, mark as INCORRECT.

**Output ONLY one word: CORRECT or INCORRECT**"""


def extract_answer(question: str, response: str) -> str:
    if not response or len(response.strip()) < 5:
        return "NO_ANSWER"

    prompt = EXTRACT_ANSWER_PROMPT.format(
        question=question,
        response=response[:8000],
    )
    try:
        result = chat_with_gpt(prompt, temperature=0.0)
        return result.strip()
    except Exception as e:
        print(f"Error extracting answer: {e}")
        return "NO_ANSWER"


def judge_answer(question: str, ground_truth: str, extracted_answer: str) -> bool:
    if not extracted_answer or extracted_answer == "NO_ANSWER":
        return False

    prompt = JUDGE_ANSWER_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        extracted_answer=extracted_answer
    )
    try:
        result = chat_with_gpt(prompt, temperature=0.0).strip().upper()
        if result == "CORRECT":
            return True
        if result == "INCORRECT":
            return False
        return result.startswith("CORRECT") and "INCORRECT" not in result
    except Exception as e:
        print(f"Error judging answer: {e}")
        return False


def load_results(results_dir: str, product_name: str) -> list:
    filepath = os.path.join(results_dir, f"{product_name}_results.jsonl")
    if not os.path.exists(filepath):
        print(f"Results file not found: {filepath}")
        return []

    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def evaluate_product(results_dir: str, product_name: str,
                     eval_output_dir: str = None, delay: float = 1.0) -> dict:
    if eval_output_dir is None:
        eval_output_dir = os.path.join(results_dir, "eval")
    os.makedirs(eval_output_dir, exist_ok=True)

    results = load_results(results_dir, product_name)
    if not results:
        return {"product": product_name, "total": 0, "answered": 0,
                "correct": 0, "accuracy": 0.0}

    eval_file = os.path.join(eval_output_dir, f"{product_name}_eval.jsonl")
    evaluated_indices = set()
    if os.path.exists(eval_file):
        with open(eval_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line.strip())
                    evaluated_indices.add(record["idx"])

    total = len(results)
    correct = 0
    answered = 0

    if os.path.exists(eval_file):
        with open(eval_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line.strip())
                    if record.get("is_correct"):
                        correct += 1
                    if record.get("extracted_answer", "NO_ANSWER") != "NO_ANSWER":
                        answered += 1

    for r in results:
        idx = r["idx"]
        if idx in evaluated_indices:
            continue

        question = r["query"]
        response = r["response"]
        ground_truth = r["ground_truth"]

        extracted = extract_answer(question, response)
        time.sleep(delay)

        is_correct = judge_answer(question, ground_truth, extracted)
        time.sleep(delay)

        eval_record = {
            "idx": idx,
            "question": question,
            "ground_truth": ground_truth,
            "extracted_answer": extracted,
            "is_correct": is_correct
        }

        with open(eval_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(eval_record, ensure_ascii=False) + "\n")

        if is_correct:
            correct += 1
        if extracted != "NO_ANSWER":
            answered += 1

        evaluated_indices.add(idx)
        print(f"[{product_name}] [{len(evaluated_indices)}/{total}] "
              f"Correct: {is_correct} | Answer: {extracted[:80]}...")

    accuracy = correct / total * 100 if total > 0 else 0.0
    return {
        "product": product_name,
        "total": total,
        "answered": answered,
        "correct": correct,
        "accuracy": round(accuracy, 2)
    }


def evaluate_all(results_dir: str = "results",
                 products: list = None) -> list:
    if products is None:
        products = [
            "perplexity", "tiangong", "ernie", "kimi",
            "metaso", "chatglm", "baichuan", "tongyi"
        ]

    all_results = []
    for product in products:
        print(f"\n{'='*60}")
        print(f"Evaluating: {product}")
        print(f"{'='*60}")
        result = evaluate_product(results_dir, product)
        all_results.append(result)
        print(f"[{product}] Total: {result['total']}, "
              f"Correct: {result['correct']}, "
              f"Accuracy: {result['accuracy']}%")

    print_summary_table(all_results)
    save_summary_csv(all_results, results_dir)
    return all_results


def print_summary_table(results: list):
    print(f"\n{'='*70}")
    print(f"{'BrowseComp Benchmark Results':^70}")
    print(f"{'='*70}")
    print(f"{'Product':<20} {'Total':>8} {'Answered':>10} {'Correct':>10} {'Accuracy':>10}")
    print(f"{'-'*70}")
    for r in sorted(results, key=lambda x: x["accuracy"], reverse=True):
        print(f"{r['product']:<20} {r['total']:>8} {r['answered']:>10} "
              f"{r['correct']:>10} {r['accuracy']:>9.2f}%")
    print(f"{'='*70}")


def save_summary_csv(results: list, results_dir: str):
    filepath = os.path.join(results_dir, "browsecomp_summary.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product", "total", "answered", "correct", "accuracy"])
        writer.writeheader()
        for r in sorted(results, key=lambda x: x["accuracy"], reverse=True):
            writer.writerow(r)
    print(f"\nSummary saved to: {filepath}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate BrowseComp results")
    parser.add_argument("--results-dir", default="results", help="Results directory")
    parser.add_argument("--product", default=None, help="Evaluate single product")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between GPT calls")
    args = parser.parse_args()

    if args.product:
        result = evaluate_product(args.results_dir, args.product, delay=args.delay)
        print(f"\n{args.product}: {result['correct']}/{result['total']} = {result['accuracy']}%")
    else:
        evaluate_all(args.results_dir)
