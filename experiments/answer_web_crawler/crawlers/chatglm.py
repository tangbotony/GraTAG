import time
from base_crawler import BaseCrawler


class ChatGLMCrawler(BaseCrawler):

    name = "chatglm"
    url = "https://chatglm.cn/"

    def login(self, phone: str = ""):
        print(f"[{self.name}] Attempting login with phone: {phone}")
        try:
            self.page.wait_for_timeout(3000)

            login_btn = self.find_element([
                'button:has-text("登录")',
                'a:has-text("登录")',
                'span:has-text("登录")',
            ])
            if login_btn:
                login_btn.click()
                self.page.wait_for_timeout(2000)

            sms_tab = self.find_element([
                'text=短信登录',
                'text=验证码登录',
                'span:has-text("短信")',
                'div:has-text("短信登录")',
            ])
            if sms_tab:
                sms_tab.click()
                self.page.wait_for_timeout(1000)

            phone_input = self.find_element([
                'input[placeholder*="手机"]',
                'input[type="tel"]',
                'input[placeholder*="phone"]',
                'input[placeholder*="请输入手机号"]',
            ])
            if phone_input:
                phone_input.fill(phone)
                self.page.wait_for_timeout(1000)

                agree = self.find_element([
                    'input[type="checkbox"]',
                    '[class*="agree"]',
                    '[class*="checkbox"]',
                ])
                if agree:
                    try:
                        agree.click()
                        self.page.wait_for_timeout(500)
                    except Exception:
                        pass

                sms_btn = self.find_element([
                    'text=获取验证码',
                    'text=发送验证码',
                    'button:has-text("验证码")',
                    'span:has-text("获取验证码")',
                ])
                if sms_btn:
                    sms_btn.click()
                    print(f"[{self.name}] 验证码已发送到 {phone}，请输入验证码：")
                    code = input("请输入验证码: ").strip()
                    code_input = self.find_element([
                        'input[placeholder*="验证码"]',
                        'input[placeholder*="code"]',
                        'input[placeholder*="请输入验证码"]',
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
                'button:has-text("新建对话")',
                'button:has-text("新对话")',
                'a:has-text("新建")',
            ], timeout=3000)
            if new_btn:
                new_btn.click()
                self.page.wait_for_timeout(2000)
                return
        except Exception:
            pass
        self.page.goto(self.url + "main/alltoolsdetail", wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

    def submit_query(self, query: str) -> str:
        try:
            textarea = self.find_element([
                'textarea',
                '[contenteditable="true"]',
                'div[role="textbox"]',
                '[class*="input-box"]',
                '[class*="editor"]',
            ])
            if textarea is None:
                print(f"[{self.name}] Cannot find input element (login required?)")
                return ""

            textarea.click()
            self.page.wait_for_timeout(500)
            self.safe_fill(textarea, query)
            self.page.wait_for_timeout(1000)

            send_btn = self.find_element([
                'button:has-text("发送")',
                '[class*="send"]',
                'button[data-testid*="send"]',
                '[class*="enter"]',
            ], timeout=3000)
            if send_btn:
                send_btn.click()
            else:
                self.page.keyboard.press("Enter")

            self.page.wait_for_timeout(10000)
            self.wait_stable("body", max_wait=180, min_length=100)

            return self._extract_response()

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return ""

    def _extract_response(self) -> str:
        for selector in [
            '[class*="bot"]',
            '[class*="assistant"]',
            '[class*="markdown-body"]',
            '[class*="answer"]',
            '[class*="markdown"]',
        ]:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    text = elements.last.inner_text()
                    if text.strip() and len(text.strip()) > 10:
                        return text.strip()
            except Exception:
                continue
        return ""
