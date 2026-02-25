"""BrowseComp evaluation orchestration: crawl / evaluate / summary."""

import sys
import os
import argparse
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ALL_PRODUCTS = [
    "perplexity", "tiangong", "ernie", "kimi",
    "metaso", "chatglm", "baichuan", "tongyi"
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(SCRIPT_DIR, "..", "query", "browse_comp_test_set_decrypted.csv")
DEFAULT_RESULTS = os.path.join(SCRIPT_DIR, "results")


def cmd_crawl(args):
    products = ALL_PRODUCTS if "all" in args.products else args.products

    for product in products:
        print(f"\n{'='*60}")
        print(f"Starting crawler: {product}")
        print(f"{'='*60}")

        cmd = [
            sys.executable, os.path.join(SCRIPT_DIR, "run_crawler.py"),
            "--product", product,
            "--data", args.data,
            "--results-dir", args.results_dir,
            "--start", str(args.start),
            "--delay", str(args.delay),
            "--batch-size", str(args.batch_size),
        ]
        if args.end is not None:
            cmd.extend(["--end", str(args.end)])
        if args.headless:
            cmd.append("--headless")

        try:
            subprocess.run(cmd, check=False)
        except KeyboardInterrupt:
            print(f"\nInterrupted during {product}. Moving to next product...")
            continue

    print("\nAll crawlers finished.")


def cmd_evaluate(args):
    from evaluate import evaluate_all, evaluate_product

    products = ALL_PRODUCTS if "all" in args.products else args.products

    if len(products) == 1:
        result = evaluate_product(args.results_dir, products[0], delay=args.delay)
        print(f"\n{products[0]}: {result['correct']}/{result['total']} = {result['accuracy']}%")
    else:
        evaluate_all(args.results_dir, products)


def cmd_summary(args):
    import json
    from evaluate import print_summary_table, save_summary_csv

    products = ALL_PRODUCTS if "all" in args.products else args.products
    eval_dir = os.path.join(args.results_dir, "eval")

    results = []
    for product in products:
        eval_file = os.path.join(eval_dir, f"{product}_eval.jsonl")
        if not os.path.exists(eval_file):
            print(f"No evaluation file for {product}, skipping...")
            continue

        total = 0
        correct = 0
        answered = 0
        with open(eval_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line.strip())
                    total += 1
                    if record.get("is_correct"):
                        correct += 1
                    if record.get("extracted_answer", "NO_ANSWER") != "NO_ANSWER":
                        answered += 1

        accuracy = correct / total * 100 if total > 0 else 0.0
        results.append({
            "product": product,
            "total": total,
            "answered": answered,
            "correct": correct,
            "accuracy": round(accuracy, 2)
        })

    if results:
        print_summary_table(results)
        save_summary_csv(results, args.results_dir)
    else:
        print("No evaluation results found.")


def main():
    parser = argparse.ArgumentParser(
        description="BrowseComp Benchmark Evaluation Pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # crawl
    crawl_parser = subparsers.add_parser("crawl", help="Run crawlers")
    crawl_parser.add_argument("--products", nargs="+", default=["all"],
                              help="Products to crawl (or 'all')")
    crawl_parser.add_argument("--data", default=DEFAULT_DATA)
    crawl_parser.add_argument("--results-dir", default=DEFAULT_RESULTS)
    crawl_parser.add_argument("--start", type=int, default=0)
    crawl_parser.add_argument("--end", type=int, default=None)
    crawl_parser.add_argument("--delay", type=float, default=5.0)
    crawl_parser.add_argument("--batch-size", type=int, default=50)
    crawl_parser.add_argument("--headless", action="store_true")

    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate results")
    eval_parser.add_argument("--products", nargs="+", default=["all"])
    eval_parser.add_argument("--results-dir", default=DEFAULT_RESULTS)
    eval_parser.add_argument("--delay", type=float, default=1.0)

    # summary
    summary_parser = subparsers.add_parser("summary", help="Generate summary")
    summary_parser.add_argument("--products", nargs="+", default=["all"])
    summary_parser.add_argument("--results-dir", default=DEFAULT_RESULTS)

    args = parser.parse_args()

    if args.command == "crawl":
        cmd_crawl(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "summary":
        cmd_summary(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
