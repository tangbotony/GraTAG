# !/usr/bin/env python3# coding:utf-8# larkbot.pyimport base64
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from include.utils.mongo_utils import User
from include.config import CommonConfig
WEBHOOK_URL = CommonConfig["WEBHOOK"]["WEBHOOK_URL"]
WEBHOOK_SECRET = CommonConfig["WEBHOOK"]["WEBHOOK_SECRET"]
EXCEPT_USER_IDS = ['test3','test2','test1']

class LarkBot:
    def __init__(self, secret: str = None) -> None:
        if not secret:
            secret = WEBHOOK_SECRET
        self.secret = secret

    def gen_sign(self, timestamp: int) -> str:
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')

        return sign

    def send_string(self, session_id, request_id, user_id, module_name, content: str) -> None:
        if user_id not in EXCEPT_USER_IDS:
            timestamp = int(datetime.now().timestamp())
            sign = self.gen_sign(timestamp)

            params = {
                "timestamp": timestamp,
                "sign": sign,
                "msg_type": "text",
                "content": {"text": content},
            }
            resp = requests.post(url=WEBHOOK_URL, json=params)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") and result["code"] != 0:
                print(result["msg"])
                return
            print("消息发送成功")

    def send_card(self, user_id, module_name, content) -> None:
        try:
            if user_id not in EXCEPT_USER_IDS:
                timestamp = int(datetime.now().timestamp())
                sign = self.gen_sign(timestamp)
                user = User.objects(_id=user_id).first()
                user_name = user.name if user else user_id

                card_json = {
                    "config": {
                        "update_multi": True
                    },
                    "i18n_elements": {
                        "zh_cn": [
                            {
                                "tag": "markdown",
                                "content": '- **User Name**: ' + user_name,
                                "text_align": "left",
                                "text_size": "normal"
                            },
                            {
                                "tag": "markdown",
                                "content": content,
                                "text_align": "left",
                                "text_size": "normal"
                            }
                        ]
                    },
                    "i18n_header": {
                        "zh_cn": {
                            "title": {
                                "tag": "plain_text",
                                "content": "☂️GraTAG☂️｜{}".format(module_name)  # 标题
                            },
                            "text_tag_list": [
                            ],
                            "template": "indigo"
                        }
                    }
                }

                params = {
                    "msg_type": "interactive",
                    "sign": sign,
                    "card": card_json
                }
                resp = requests.post(url=WEBHOOK_URL, json=params)
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") and result["code"] != 0:
                    print(result["msg"])
                    return
                print("消息发送成功")
        except:
            print("消息发送失败")


def main():
    bot = LarkBot(secret=WEBHOOK_SECRET)
    bot.send_string(
        "session_id",
        "request_id",
        "user_id", "self.module_name",
        "这是一条消息"
    )
    # 搭建消息卡片教程：
    # https://open.feishu.cn/document/common-capabilities/message-card/getting-started/send-message-cards-with-a-custom-bot
    # https://open.feishu.cn/cardkit
    bot.send_card("zhiyulee@xinyunews.cn", "self.module_name",
                  "- **Query：{}**\n "
                  "- **application：{}**\n "
                  "- **共召回{}张图片**\n "
                  "- **共召回{}条参考材料** \n"
                  "- **参考材料分布** \n{}".format("query", "application", "num_fig", "num_ref", "all_ref_distribution")
        )


if __name__ == '__main__':
    main()
