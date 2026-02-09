import re
from datetime import datetime, timedelta
from time import time
import os
import requests
import json

interfaces = dict()
users_set = set()

log_pattern = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - '
    r'(?P<file_path>.*?)(?:\[line:(?P<line_number>\d+)\])? - '
    r'(?P<log_level>INFO|ERROR|WARNING|DEBUG): '
    r'(?P<json_data>\{.*\})'
)
def send_feishu_message(message, url):
    header = {"Content-Type": "application/json"}
    data = {
        "msg_type":"text","content":{"text":message}
    }
    data = json.dumps(data)
    requests.post(url=url, headers=header, data=data)
    print(f"{message}")

def parse_single_line(log_line):
    match = log_pattern.match(log_line)
    if not match:
        return

    log_data = match.groupdict()

    timestamp_str = log_data['timestamp']
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')

    log_data['json_data'] = eval(log_data['json_data'])

    if yesterday.date() == timestamp.date() and log_data['log_level'] != 'ERROR':
        url = log_data['json_data']['url']
        ip = log_data['json_data']['ip']

        if url in interfaces.keys():
            interfaces[url] += 1
        else:
            interfaces[url] = 1
        
        users_set.add(ip)

today= datetime.today()
yesterday = today - timedelta(days=1)
day_before_yes = today - timedelta(days=2)
text = ""

log_path_dby = f"~/docker/logs/back/monitor.log.{day_before_yes.date()}"
log_path_yes = f"~/docker/logs/back/monitor.log.{yesterday.date()}"
log_path_tdy = f"~/docker/logs/back/monitor.log"

if not os.path.exists(log_path_dby) and not os.path.exists(log_path_yes) and not os.path.exists(log_path_tdy):
    text = "昨日环境后端访问量无数据"
    send_feishu_message(text)
    exit(1)

for _log in [log_path_dby, log_path_yes, log_path_tdy]:
    if not os.path.exists(_log): continue
    with open(_log, "r") as f:
        lines = f.readlines()
        for line in lines:
            parse_single_line(line)


text += f"昨日({yesterday.date()})后端访问量统计：\n"
text += f"访问用户总数量: {len(users_set)} 个\n"
text += f"访问接口总数量: {len(interfaces)} 个\n"
# for key in interfaces.keys():
#     if "heartbeat" in key: continue
#     text += f"接口{key}: {interfaces[key]} 次\n"

send_feishu_message(text)


