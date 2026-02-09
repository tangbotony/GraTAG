import requests
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from include.config import CommonConfig
from datetime import datetime
import hmac
import base64
import hashlib
import subprocess
import time
import urllib.parse

def env_test_release_bot(branch,release_time,pass_rate,test_detail,title,title_color):
    ## 替换为你的自定义机器人的 webhook 地址。
    url = CommonConfig["RELEASE_BOT"]["TEST_ENV_WEBHOOK_URL"]
    secret = CommonConfig["RELEASE_BOT"]["TEST_ENV_WEBHOOK_SECRET"]
    timestamp = int(datetime.now().timestamp())
    sign = gen_sign(timestamp,secret)
    ## 将消息卡片内容粘贴至此处。
    card_json = {
        "config": {
            "update_multi": True
        },
        "i18n_elements": {
            "zh_cn": [
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "vertical_align": "top",
                            "vertical_spacing": "2px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": f"**发版项目：**{branch}",
                                    "text_align": "left",
                                    "text_size": "normal",
                                    "icon": {
                                        "tag": "standard_icon",
                                        "token": "assigned_outlined"
                                    }
                                }
                            ],
                            "weight": 1
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "vertical_align": "top",
                            "vertical_spacing": "8px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": f"**时间：**{release_time}",
                                    "text_align": "left",
                                    "text_size": "normal",
                                    "icon": {
                                        "tag": "standard_icon",
                                        "token": "time_outlined"
                                    }
                                }
                            ],
                            "weight": 1
                        }
                    ],
                    "margin": "16px 0px 0px 0px"
                },
                {
                    "tag": "column_set",
                    "flex_mode": "stretch",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "vertical_align": "top",
                            "vertical_spacing": "8px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": "**测试通过率：**\n"+str(pass_rate),
                                    "text_align": "left",
                                    "text_size": "normal",
                                    "icon": {
                                        "tag": "standard_icon",
                                        "token": "label-change_outlined"
                                    }
                                }
                            ],
                            "weight": 1
                        }
                    ],
                    "margin": "16px 0px 0px 0px"
                },
                {
                    "tag": "markdown",
                    "content": f"**测试详情：**\n{test_detail}",
                    "text_align": "left",
                    "text_size": "normal",
                    "icon": {
                        "tag": "standard_icon",
                        "token": "readinfo_outlined"
                    }
                }
            ]
        },
        "i18n_header": {
            "zh_cn": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{title}"
                },
                "subtitle": {
                    "tag": "plain_text",
                    "content": ""
                },
                "template": f"{title_color}",
                "ud_icon": {
                    "tag": "standard_icon",
                    "token": "approval_colorful"
                }
            }
        }
    }
    body = json.dumps({"msg_type": "interactive", "card": card_json,"sign": sign,"timestamp": timestamp})
    headers = {"Content-Type": "application/json"}
    result = requests.post(url=url, data=body, headers=headers)
    res=json.loads(result.text)
    if res.get("code") and res["code"] != 0:
        print(res["msg"])
        return
    print("消息发送成功")

def gen_sign(timestamp,secret):
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

class DingTalkRobot:
    def __init__(self, token, secret, user_ids=None):
        self.token = token
        self.secret = secret
        self.user_ids = user_ids or []

    def _generate_signature(self):
        timestamp = str(round(time.time() * 1000))
        secret = self.secret

        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()

        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def send_markdown(self, title, content, at_all=False):
        timestamp, sign = self._generate_signature()

        url = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}" \
              f"&timestamp={timestamp}&sign={sign}"

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            },
            "at": {
                "atUserIds": self.user_ids,
                "isAtAll": at_all
            }
        }

        response = requests.post(url, json=data, headers=headers)
        return response.json()
def env_test_release_bot_dingding(branch,release_time,pass_rate,test_detail,title,title_color):
    CUSTOM_ROBOT_TOKEN = CommonConfig["RELEASE_BOT_DD"]["ROBOT_TOKEN"]
    SECRET = CommonConfig["RELEASE_BOT_DD"]["ROBOT_SECRET"]
    USER_ID = CommonConfig["RELEASE_BOT_DD"]["USER_ID"]
    robot = DingTalkRobot(
        token=CUSTOM_ROBOT_TOKEN,
        secret=SECRET,
        user_ids=USER_ID
    )
    if "未通过" in title:
        pass_markdown_content = f"""
### ❌**发版测试未通过:{branch}**  

| 字段 | 内容 |
|------|------|
| **发版项目** | AINews: {branch} |
| **时间** | {release_time} |
| **测试通过率** | ✅ {pass_rate}|

**📊 测试详情**  
{test_detail}
             """
    else:
        pass_markdown_content = f"""
### ✅**发版测试通过:{branch}**  

| 字段 | 内容 |
|------|------| 
| **发版项目** | AINews: {branch} |
| **时间** | {release_time} |
| **测试通过率** | ✅ {pass_rate}|

**📊 测试详情**  
{test_detail}
             """
    result = robot.send_markdown(title, pass_markdown_content)
    print("消息发送结果",result)


def get_current_git_branch():
    try:
        # Run the 'git branch' command and capture the output
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        # The output will be the branch name
        branch_name = result.stdout.strip()
        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e.stderr}")
        return None

if __name__=="__main__":
    pass_rate="100%"
    if pass_rate=="100%":
        test_tile="测试通过"
        color="green"
    else:
        test_tile = "测试通过"
        color = "red"
    test_detail = f"<font color = 'green' > 时间线通过 <font >测试通过\n"+f"<font color = 'red' > 问答不通过 <font>测试不通过\n"

    # test_detail="时间线通过\n补充问题通过\n问答通过\n追问推荐通过"
    branch="test_pipeline_gyh"
    test_time=datetime.now()
    # 获取当前日期和时间
    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # print("格式化后的日期和时间是：", formatted_time)
    # env_test_release_bot(branch=branch,release_time=formatted_time,pass_rate=pass_rate,test_detail=test_detail,title=test_tile,title_color=color)
    env_test_release_bot_dingding(branch=branch, release_time=formatted_time, pass_rate=pass_rate, test_detail=test_detail,
                         title=test_tile, title_color=color)