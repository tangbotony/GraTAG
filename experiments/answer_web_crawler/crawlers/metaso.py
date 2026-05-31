import time
from base_crawler import BaseCrawler


class MetasoCrawler(BaseCrawler):

    name = "metaso"
    url = "https://metaso.cn/"

    def login(self, phone: str = ""):
        print(f"[{self.name}] Attempting login with phone: {phone}")
        try:
            login_trigger = self.page.locator(
                'text=登录, button:has-text("登录"), a:has-text("登录")'
            ).first
            if login_trigger.is_visible(timeout=5000):
                login_trigger.click()
                self.page.wait_for_timeout(2000)

            phone_input = self.page.locator(
                'input[placeholder*="手机"], input[type="tel"], input[placeholder*="phone"]'
            ).first
            if phone_input.is_visible(timeout=5000):
                phone_input.fill(phone)
                self.page.wait_for_timeout(1000)

                sms_btn = self.page.locator(
                    'text=获取验证码, text=发送验证码, button:has-text("验证码")'
                ).first
                if sms_btn.is_visible(timeout=3000):
                    sms_btn.click()
                    print(f"[{self.name}] 验证码已发送到 {phone}，请输入验证码：")
                    code = input("请输入验证码: ").strip()
                    code_input = self.page.locator(
                        'input[placeholder*="验证码"], input[placeholder*="code"]'
                    ).first
                    code_input.fill(code)
                    self.page.wait_for_timeout(1000)

                    submit_btn = self.page.locator(
                        'button:has-text("登录"), button[type="submit"]'
                    ).first
                    if submit_btn.is_visible(timeout=3000):
                        submit_btn.click()
                    self.page.wait_for_timeout(5000)
                    print(f"[{self.name}] Login completed.")
            else:
                print(f"[{self.name}] No login form or already logged in.")
        except Exception as e:
            print(f"[{self.name}] Login: {e}")

    def start_new_chat(self):
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

    def submit_query(self, query: str) -> str:
        try:
            textarea = None
            for selector in [
                'textarea.search-consult-textarea',
                'textarea[placeholder*="请输入"]',
                'textarea',
                '[contenteditable="true"]',
            ]:
                el = self.page.locator(selector).first
                try:
                    if el.is_visible(timeout=3000):
                        textarea = el
                        break
                except Exception:
                    continue

            if textarea is None:
                print(f"[{self.name}] Cannot find input element")
                return ""

            textarea.click()
            textarea.fill(query)
            self.page.wait_for_timeout(1000)

            submitted = False
            for selector in [
                'button.send-arrow-button',
                'button:has-text("搜索")',
                'button:has-text("发送")',
                'button[type="submit"]',
            ]:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000) and btn.is_enabled(timeout=1000):
                        btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if not submitted:
                textarea.press("Enter")

            self.page.wait_for_timeout(8000)
            self._wait_for_response()

            return self._extract_response()

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return ""

    def _extract_response(self) -> str:
        for selector in [
            '[class*="answer"]',
            '[class*="result-content"]',
            '[class*="markdown"]',
            '[class*="ai-answer"]',
            '[class*="search-result"]',
            'article',
        ]:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    texts = []
                    for i in range(elements.count()):
                        t = elements.nth(i).inner_text()
                        if t.strip() and len(t.strip()) > 20:
                            texts.append(t.strip())
                    if texts:
                        return "\n\n".join(texts)
            except Exception:
                continue

        try:
            return self.page.locator("main, #root, #app").first.inner_text()
        except Exception:
            return ""

    def _wait_for_response(self, max_wait: int = 120):
        start = time.time()
        prev_len = 0
        stable_count = 0

        while time.time() - start < max_wait:
            try:
                body = self.page.locator("main, #root, body").first.inner_text()
                curr_len = len(body)
                if curr_len > 200 and curr_len == prev_len:
                    stable_count += 1
                    if stable_count >= 4:
                        break
                else:
                    stable_count = 0
                prev_len = curr_len
            except Exception:
                pass
            self.page.wait_for_timeout(3000)
        self.page.wait_for_timeout(2000)
