from app import app
from config import config_manager, nacos_client, nacos_config
import setproctitle
import re
import os
import time
proc_title = config_manager.prometheus_config['process_name']
setproctitle.setproctitle(proc_title)


# 验证 ipv4
def is_valid_ipv4(ip):
    if ip is None:
        return False
    pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if pattern.match(ip):
        # 确保每个数字在 0-255 之间
        parts = ip.split('.')
        for part in parts:
            if int(part) < 0 or int(part) > 255:
                return False
        return True
    return False



ip = os.getenv('NACOS_HOST_IP', None)

# 如果获取 ip 失败，则直接报错
if nacos_config['REGISTRATION_SWITCH'] == 'true' and not is_valid_ipv4(ip):
    print(ip)
    raise(Exception("没有获取合适 ip"))

# 每5秒发送一次心跳
def send_heartbeat():
    while True:
        # print("dasd")
        nacos_client.send_heartbeat(service_name=nacos_config['SERVICE_NAME'], cluster_name=nacos_config['CLUSTER_NAME'], ip=ip, port=config_manager.default_config['Port'])
        time.sleep(3)





import threading
if "__main__" == __name__:

    # 注册服务
    if nacos_config['REGISTRATION_SWITCH'] == 'true':
        nacos_client.add_naming_instance(service_name=nacos_config['SERVICE_NAME'], cluster_name=nacos_config['CLUSTER_NAME'], ip=ip, port=config_manager.default_config['Port'])

    heartbeat_thread = threading.Thread(target=send_heartbeat)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    app.run(host=config_manager.default_config['Host'], port=config_manager.default_config['Port'])
    
    # app.run(host=config['DEFAULT']['Host'], port=config['DEFAULT']['Port'])



