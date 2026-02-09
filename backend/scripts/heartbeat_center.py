import requests
import json
from datetime import datetime, timedelta
import yaml

max_retry = 3
headers = {
   'token': 'xxxxx',
   'Accept': '*/*',
   'Connection': 'keep-alive',
   'function': 'receive_heartbeat',
}
payload={}

def send_feishu_message(message, url):
    header = {"Content-Type": "application/json"}
    data = {
        "msg_type":"text","content":{"text":message}
    }
    data = json.dumps(data)
    requests.post(url=url, headers=header, data=data)
    print(f"{message} {datetime.now()}")

def retry_request(service, url, method='POST'):
    success = False
    for _ in range(max_retry):
        response = requests.request(method, url, headers=headers, data=payload)
        if response.status_code == 200:
            success = True
            return
    if success == False: # 服务宕机，判断是否处于冷却期，决定是否发送到报警群
        in_cooldown = read_cooldown(service)
        # 若在冷却期，则直接退出
        if in_cooldown: return
        # 若不在冷却期，则发送消息，设置新的冷却期
        else:
            send_feishu_message(f"{service} doesn't work: {response.reason}")
            write_cooldown(service)

def write_cooldown(target_service_name):
    try:
        with open('./cooldown_file.yaml', 'r') as f:
            data = yaml.safe_load(f)
        # 设置新的冷却时间
        services = data.get('services', [])
        for service in services:
            if service.get("service_name") == target_service_name:
                new_cooldown_time = (datetime.now() + timedelta(hours=0.5)).strftime('%Y-%m-%d %H:%M:%S')
                service['cooldown_time'] = new_cooldown_time
        data['services'] = services

        with open('./cooldown_file.yaml', 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
    except FileNotFoundError:
        print("Cooldown file not found in write_cooldown.")
        return
    except Exception as e:
        print(f"An unexpected error occurred in write_cooldown: {e}")
        return

def read_cooldown(target_service_name):
    try:
        with open('./cooldown_file.yaml', 'r') as f:
            data = yaml.safe_load(f)
        services = data.get('services', [])
        for service in services:
            if service.get("service_name") == target_service_name:
                cooldown_time_str = service.get("cooldown_time")
        # 若文件中冷却时间还未设置过，则认为不在冷却期内
        if cooldown_time_str is None:
            return False
        # 比较当前时间，确定是否在冷却期内
        now_time = datetime.now()
        cooldown_time = datetime.strptime(cooldown_time_str, '%Y-%m-%d %H:%M:%S')
        if cooldown_time < now_time: return False # 若已过冷却时间
        else: return True
    except FileNotFoundError:
        print("Cooldown file not found in read_cooldown.")
        return True
    except Exception as e:
        print(f"An unexpected error occurred in read_cooldown: {e}")
        return True