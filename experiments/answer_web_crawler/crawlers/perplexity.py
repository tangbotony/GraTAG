import time
import urllib.parse
from base_crawler import BaseCrawler


class PerplexityCrawler(BaseCrawler):

    name = "perplexity"
    url = "https://www.perplexity.ai/"

    def login(self, phone: str = ""):
        print(f"[{self.name}] Perplexity supports anonymous mode, skipping login.")
        self.page.wait_for_timeout(3000)
        self._dismiss_popups()

    def _dismiss_popups(self):
        try:
            for selector in [
                'button:has-text("Accept")', 'button:has-text("Got it")',
                'button:has-text("Close")', '[aria-label="Close"]',
                'button:has-text("Continue")', 'button:has-text("OK")',
                'button:has-text("Agree")',
            ]:
                btn = self.page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    self.page.wait_for_timeout(500)
        except Exception:
            pass

    def start_new_chat(self):
        pass

    def submit_query(self, query: str) -> str:
        try:
            encoded_q = urllib.parse.quote(query)
            search_url = f"https://www.perplexity.ai/search?q={encoded_q}"
            self.page.goto(search_url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
            self._dismiss_popups()

            self.page.wait_for_timeout(10000)
            self.wait_stable("body", max_wait=120, min_length=200)

            return self._extract_response(query)

        except Exception as e:
            print(f"[{self.name}] Error in submit_query: {e}")
            return ""

    def _extract_response(self, query: str) -> str:
        full_text = ""
        for selector in [
            '[class*="prose"]',
            '[class*="markdown"]',
            '[class*="answer"]',
            '[class*="result"]',
            'article',
        ]:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    texts = []
                    for i in range(elements.count()):
                        t = elements.nth(i).inner_text()
                        if t.strip() and len(t.strip()) > 30:
                            if query[:50] not in t[:60]:
                                texts.append(t.strip())
                    if texts:
                        full_text = "\n\n".join(texts)
                        break
            except Exception:
                continue

        if not full_text:
            try:
                body = self.page.locator("main, body").first.inner_text()
                lines = body.split("\n")
                filtered = [l.strip() for l in lines
                            if l.strip() and len(l.strip()) > 20
                            and query[:40] not in l[:50]]
                full_text = "\n".join(filtered)
            except Exception:
                pass

        return full_text
