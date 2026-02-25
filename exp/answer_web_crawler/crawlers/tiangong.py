import time
import urllib.parse
from base_crawler import BaseCrawler


class TiangongCrawler(BaseCrawler):

    name = "tiangong"
    url = "https://www.tiangong.cn/"

    def login(self, phone: str = ""):
        print(f"[{self.name}] Attempting login with phone: {phone}")
        self._accept_terms()

        try:
            phone_input = self.find_element([
                'input[type="tel"]',
                'input[placeholder*="手机"]',
                'input[placeholder*="phone"]',
            ])
            if phone_input:
                phone_input.fill(phone)
                self.page.wait_for_timeout(1000)

                sms_btn = self.find_element([
                    'text=获取验证码',
                    'text=发送验证码',
                    'button:has-text("验证码")',
                ])
                if sms_btn:
                    sms_btn.click()
                    print(f"[{self.name}] 验证码已发送到 {phone}，请输入验证码：")
                    code = input("请输入验证码: ").strip()
                    code_input = self.find_element([
                        'input[placeholder*="验证码"]',
                        'input[placeholder*="code"]',
                    ])
                    if code_input:
                        code_input.fill(code)
                    self.page.wait_for_timeout(1000)

                    confirm_btn = self.find_element([
                        'button:has-text("登录")',
                        'button[type="submit"]',
                    ])
                    if confirm_btn:
                        confirm_btn.click()
                    self.page.wait_for_timeout(5000)
                    print(f"[{self.name}] Login completed.")
            else:
                print(f"[{self.name}] No login required or already logged in.")
        except Exception as e:
            print(f"[{self.name}] Login attempt: {e}")

    def _accept_terms(self):
        try:
            for selector in [
                'text=我已阅读并同意',
                'input[type="checkbox"]',
                '[class*="agree"]',
                '[class*="checkbox"]',
            ]:
                el = self.page.locator(selector).first
                if el.is_visible(timeout=3000):
                    el.click()
                    self.page.wait_for_timeout(500)
                    break
        except Exception:
            pass

        try:
            for selector in [
                'button:has-text("同意")',
                'button:has-text("确认")',
                'button:has-text("进入")',
                'button:has-text("开始")',
                'button:has-text("注册")',
            ]:
                btn = self.page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    self.page.wait_for_timeout(2000)
                    break
        except Exception:
            pass

    def start_new_chat(self):
        pass

    def submit_query(self, query: str) -> str:
        try:
            try:
                self.page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                self.page.goto(self.url, wait_until="commit", timeout=15000)
            self.page.wait_for_timeout(3000)
            self._accept_terms()

            textarea = self.find_element([
                'textarea',
                'input[type="text"]',
                '[contenteditable="true"]',
                '[placeholder*="搜索"]',
                '[placeholder*="输入"]',
                '[placeholder*="问"]',
            ])
            if textarea is None:
                print(f"[{self.name}] Cannot find input element, trying URL approach")
                encoded_q = urllib.parse.quote(query)
                self.page.goto(f"https://www.tiangong.cn/search?q={encoded_q}",
                               wait_until="domcontentloaded")
                self.page.wait_for_timeout(10000)
                self.wait_stable("body", max_wait=120, min_length=200)
                return self._extract_response(query)

            textarea.click()
            self.safe_fill(textarea, query)
            self.page.wait_for_timeout(1000)

            submit_btn = self.find_element([
                'button[type="submit"]',
                'button:has-text("搜索")',
                'button:has-text("发送")',
            ], timeout=3000)
            if submit_btn:
                submit_btn.click()
            else:
                self.page.keyboard.press("Enter")

            self.page.wait_for_timeout(10000)
            self.wait_stable("body", max_wait=120, min_length=200)

            return self._extract_response(query)

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return ""

    def _extract_response(self, query: str) -> str:
        for selector in [
            '[class*="answer"]',
            '[class*="result"]',
            '[class*="markdown"]',
            '[class*="content"]',
            '[class*="response"]',
        ]:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    texts = []
                    for i in range(elements.count()):
                        t = elements.nth(i).inner_text()
                        if (t.strip() and len(t.strip()) > 30
                                and query[:40] not in t[:50]):
                            texts.append(t.strip())
                    if texts:
                        return "\n\n".join(texts)
            except Exception:
                continue

        try:
            body = self.page.locator("main, #app, body").first.inner_text()
            lines = body.split("\n")
            filtered = [l.strip() for l in lines
                        if l.strip() and len(l.strip()) > 20
                        and query[:40] not in l[:50]
                        and "京公网安备" not in l
                        and "ICP" not in l
                        and "版权所有" not in l
                        and "服务条款" not in l
                        and "隐私政策" not in l]
            return "\n".join(filtered)
        except Exception:
            return ""
