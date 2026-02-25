"""Run a single crawler for a specific AI search product."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_crawler import load_browsecomp_data
from crawlers import CRAWLER_MAP


def main():
    parser = argparse.ArgumentParser(description="Run BrowseComp crawler for a single product")
    parser.add_argument("--product", required=True, choices=list(CRAWLER_MAP.keys()),
                        help="AI search product to crawl")
    parser.add_argument("--data", default=None,
                        help="Path to BrowseComp CSV file")
    parser.add_argument("--results-dir", default="results",
                        help="Directory to save results")
    parser.add_argument("--start", type=int, default=0,
                        help="Start index (inclusive)")
    parser.add_argument("--end", type=int, default=None,
                        help="End index (exclusive)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between queries (seconds)")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Restart browser every N queries")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode")
    parser.add_argument("--phone", default="",
                        help="Phone number for login")
    parser.add_argument("--skip-login", action="store_true",
                        help="Skip login step (for products that allow anonymous usage)")
    args = parser.parse_args()

    if args.data is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        args.data = os.path.join(script_dir, "..", "query", "browse_comp_test_set_decrypted.csv")

    queries = load_browsecomp_data(args.data)
    print(f"Loaded {len(queries)} queries from BrowseComp dataset")

    CrawlerClass = CRAWLER_MAP[args.product]
    crawler = CrawlerClass(
        headless=args.headless,
        results_dir=args.results_dir,
    )

    crawler.run(
        queries=queries,
        start_idx=args.start,
        end_idx=args.end,
        batch_size=args.batch_size,
        delay=args.delay,
        skip_login=args.skip_login,
    )


if __name__ == "__main__":
    main()
