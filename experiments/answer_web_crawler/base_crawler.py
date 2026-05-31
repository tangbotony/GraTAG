import json
import os
import time
import csv
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright, Page, Browser


class BaseCrawler(ABC):

    name: str = "base"
    url: str = ""

    def __init__(self, headless: bool = False, results_dir: str = "results",
                 slow_mo: int = 300, timeout: int = 60000):
        self.headless = headless
        self.results_dir = results_dir
        self.slow_mo = slow_mo
        self.timeout = timeout
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self._results_file = os.path.join(results_dir, f"{self.name}_results.jsonl")
        self._progress_file = os.path.join(results_dir, f"{self.name}_progress.json")
        os.makedirs(results_dir, exist_ok=True)

    def start_browser(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        self.page = context.new_page()
        self.page.set_default_timeout(self.timeout)

    def stop_browser(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def navigate(self):
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

    def find_element(self, selectors: list, timeout: int = 5000):
        for selector in selectors:
            try:
                el = self.page.locator(selector).first
                if el.is_visible(timeout=min(timeout, 3000)):
                    return el
            except Exception:
                continue
        return None

    def safe_fill(self, element, text: str):
        try:
            is_ce = element.evaluate("el => el.contentEditable === 'true'")
            if is_ce:
                element.click()
                self.page.keyboard.type(text, delay=8)
            else:
                element.fill(text)
        except Exception:
            element.fill(text)

    def wait_stable(self, selector: str = "body", max_wait: int = 180,
                    interval: int = 3000, stable_threshold: int = 3,
                    min_length: int = 50):
        start = time.time()
        prev_text = ""
        stable_count = 0
        while time.time() - start < max_wait:
            try:
                curr_text = self.page.locator(selector).first.inner_text()
                if len(curr_text) > min_length and curr_text == prev_text:
                    stable_count += 1
                    if stable_count >= stable_threshold:
                        break
                else:
                    stable_count = 0
                prev_text = curr_text
            except Exception:
                pass
            self.page.wait_for_timeout(interval)
        self.page.wait_for_timeout(2000)

    @abstractmethod
    def login(self, phone: str = ""):
        pass

    @abstractmethod
    def submit_query(self, query: str) -> str:
        pass

    @abstractmethod
    def start_new_chat(self):
        pass

    def load_progress(self) -> set:
        if os.path.exists(self._progress_file):
            with open(self._progress_file, "r") as f:
                data = json.load(f)
                return set(data.get("completed", []))
        return set()

    def save_progress(self, completed: set):
        with open(self._progress_file, "w") as f:
            json.dump({"completed": sorted(list(completed))}, f)

    def save_result(self, idx: int, query: str, response: str, ground_truth: str):
        with open(self._results_file, "a", encoding="utf-8") as f:
            record = {
                "idx": idx,
                "query": query,
                "response": response,
                "ground_truth": ground_truth,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def run(self, queries: list, start_idx: int = 0, end_idx: int = None,
            batch_size: int = 50, delay: float = 5.0, skip_login: bool = False):
        if end_idx is None:
            end_idx = len(queries)

        completed = self.load_progress()
        total = end_idx - start_idx
        done = len([i for i in range(start_idx, end_idx) if i in completed])
        print(f"[{self.name}] Starting: {done}/{total} already completed")

        try:
            self.start_browser()
            self.navigate()
            if not skip_login:
                self.login()

            for i in range(start_idx, end_idx):
                if i in completed:
                    continue

                q = queries[i]
                query_text = q["problem"]
                ground_truth = q["answer"]

                print(f"[{self.name}] [{i+1}/{end_idx}] Processing query...")
                try:
                    self.start_new_chat()
                    time.sleep(2)
                    response = self.submit_query(query_text)

                    if response and len(response.strip()) > 0:
                        self.save_result(i, query_text, response, ground_truth)
                        completed.add(i)
                        self.save_progress(completed)
                        print(f"[{self.name}] [{i+1}/{end_idx}] OK - got {len(response)} chars")
                    else:
                        print(f"[{self.name}] [{i+1}/{end_idx}] WARN - empty response")

                except Exception as e:
                    print(f"[{self.name}] [{i+1}/{end_idx}] ERROR: {e}")

                time.sleep(delay)

                if (i - start_idx + 1) % batch_size == 0:
                    print(f"[{self.name}] Restarting browser after {batch_size} queries...")
                    self.stop_browser()
                    time.sleep(5)
                    self.start_browser()
                    self.navigate()

        except KeyboardInterrupt:
            print(f"\n[{self.name}] Interrupted. Progress saved.")
        finally:
            self.save_progress(completed)
            self.stop_browser()

        print(f"[{self.name}] Finished: {len(completed)}/{total} completed")


def load_browsecomp_data(csv_path: str) -> list:
    queries = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append({
                "problem": row["problem"],
                "answer": row["answer"],
                "problem_topic": row.get("problem_topic", ""),
            })
    return queries
