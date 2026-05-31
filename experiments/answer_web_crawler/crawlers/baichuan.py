import time
from base_crawler import BaseCrawler


class BaichuanCrawler(BaseCrawler):

    name = "baichuan"
    url = "https://ying.baichuan-ai.com/"

    def login(self, phone: str = ""):
        print(f"[{self.name}] Attempting login with phone: {phone}")
        try:
            self.page.wait_for_timeout(3000)

            login_btn = self.find_element([
                'button:has-text("登录")',
                'a:has-text("登录")',
                'text=登录',
            ])
            if login_btn:
                login_btn.click()
                self.page.wait_for_timeout(2000)

            phone_input = self.find_element([
                'input[placeholder*="手机"]',
                'input[type="tel"]',
                'input[placeholder*="phone"]',
                'input[placeholder*="请输入"]',
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

                    submit_btn = self.find_element([
                        'button:has-text("登录")',
                        'button[type="submit"]',
                    ])
                    if submit_btn:
                        submit_btn.click()
                    self.page.wait_for_timeout(5000)
                    print(f"[{self.name}] Login completed.")
            else:
                print(f"[{self.name}] No login form or already logged in.")
        except Exception as e:
            print(f"[{self.name}] Login: {e}")

    def start_new_chat(self):
        try:
            new_btn = self.find_element([
                'button:has-text("新对话")',
                'button:has-text("新建")',
                '[class*="new"]',
                'a:has-text("新")',
            ], timeout=3000)
            if new_btn:
                new_btn.click()
                self.page.wait_for_timeout(2000)
                return
        except Exception:
            pass
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

    def submit_query(self, query: str) -> str:
        try:
            textarea = self.find_element([
                'textarea',
                '[contenteditable="true"]',
                'div[role="textbox"]',
                '[class*="input"]',
                '[class*="editor"]',
            ])
            if textarea is None:
                print(f"[{self.name}] Cannot find input element")
                return ""

            textarea.click()
            self.page.wait_for_timeout(500)
            self.safe_fill(textarea, query)
            self.page.wait_for_timeout(1000)

            send_btn = self.find_element([
                'button:has-text("发送")',
                '[class*="send"]',
            ], timeout=3000)
            if send_btn:
                send_btn.click()
            else:
                self.page.keyboard.press("Enter")

            self.page.wait_for_timeout(8000)
            self.wait_stable("body", max_wait=180)

            return self._extract_response()

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return ""

    def _extract_response(self) -> str:
        for selector in [
            '[class*="assistant"]',
            '[class*="bot"]',
            '[class*="markdown"]',
            '[class*="answer"]',
        ]:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    return elements.last.inner_text()
            except Exception:
                continue
        return ""
