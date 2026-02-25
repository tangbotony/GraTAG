import time
from base_crawler import BaseCrawler


class ErnieCrawler(BaseCrawler):

    name = "ernie"
    url = "https://yiyan.baidu.com/"

    def login(self, phone: str = ""):
        print(f"[{self.name}] Attempting login...")
        try:
            login_btn = self.find_element([
                'a:has-text("登录")',
                'button:has-text("登录")',
                'text=登录',
            ])
            if login_btn:
                login_btn.click()
                self.page.wait_for_timeout(3000)

            sms_login = self.find_element([
                'text=短信登录',
                'text=手机号登录',
                'a:has-text("短信")',
                'span:has-text("短信")',
            ])
            if sms_login:
                sms_login.click()
                self.page.wait_for_timeout(1000)

            phone_input = self.find_element([
                'input[name="phone"]',
                'input[placeholder*="手机"]',
                'input[type="tel"]',
                'input[id*="phone"]',
            ])
            if phone_input:
                phone_input.fill(phone)
                self.page.wait_for_timeout(1000)

                sms_btn = self.find_element([
                    'text=获取验证码',
                    'text=发送验证码',
                    'button:has-text("验证码")',
                    'a:has-text("验证码")',
                ])
                if sms_btn:
                    sms_btn.click()
                    print(f"[{self.name}] 验证码已发送到 {phone}，请输入验证码：")
                    code = input("请输入验证码: ").strip()
                    code_input = self.find_element([
                        'input[placeholder*="验证码"]',
                        'input[name*="code"]',
                        'input[name*="vcode"]',
                    ])
                    if code_input:
                        code_input.fill(code)
                    self.page.wait_for_timeout(1000)

                    submit_btn = self.find_element([
                        'button:has-text("登录")',
                        'button[type="submit"]',
                        'input[type="submit"]',
                    ])
                    if submit_btn:
                        submit_btn.click()
                    self.page.wait_for_timeout(5000)
                    print(f"[{self.name}] Login completed.")
            else:
                print(f"[{self.name}] No login form found or already logged in.")
        except Exception as e:
            print(f"[{self.name}] Login attempt: {e}")

    def start_new_chat(self):
        try:
            new_chat = self.find_element([
                '[class*="new-chat"]',
                'button:has-text("新对话")',
                'button:has-text("新建")',
                'a:has-text("新对话")',
            ], timeout=3000)
            if new_chat:
                new_chat.click()
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
                '#chat-input',
                '[class*="editor"]',
            ])
            if textarea is None:
                print(f"[{self.name}] Cannot find input element")
                return ""

            textarea.click()
            self.page.wait_for_timeout(500)
            self.safe_fill(textarea, query)
            self.page.wait_for_timeout(1000)

            submit_btn = self.find_element([
                'button:has-text("发送")',
                '[class*="send"]',
                '[class*="submit"]',
                'button[aria-label*="send"]',
            ], timeout=3000)
            if submit_btn:
                submit_btn.click()
            else:
                self.page.keyboard.press("Enter")

            self.page.wait_for_timeout(8000)
            self.wait_stable("body", max_wait=120)

            return self._extract_response()

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return ""

    def _extract_response(self) -> str:
        for selector in [
            '[class*="markdown"]',
            '[class*="answer"]',
            '[class*="bot-content"]',
            '[class*="response"]',
            '[class*="assistant"]',
        ]:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    return elements.last.inner_text()
            except Exception:
                continue
        return ""
