from flask import Flask, g, request
import importlib
import json
import os
import uuid
from flask_mongoengine import MongoEngine
from include.config import CommonConfig
from include.utils.skywalking_utils import trace_new, start_sw

app = Flask(__name__)

app.config['MONGODB_SETTINGS'] = {
    'db':   CommonConfig['MONGODB']['DB'],
    'host': CommonConfig['MONGODB']['Host'],
    'port': CommonConfig['MONGODB']['Port'],
    'username': CommonConfig['MONGODB']['Username'],
    'password': CommonConfig['MONGODB']['Password'],
    'authentication_source': CommonConfig['MONGODB']['authDB'],
}

MongoEngine(app)

from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Application info', version='1.0.3')

script_directory = os.path.dirname(os.path.abspath(__file__))

# 从配置文件中加载路由配置
with open(os.path.join(script_directory, 'route.json'), 'r') as f:
    routes = json.load(f)

@app.before_request
def generate_trace_id():
    g.session_id = request.headers.get('session_id', str(uuid.uuid4()))
    g.request_id = request.headers.get('request_id', str(uuid.uuid4()))

# 自动注册函数到路由
for function_path, config in routes.items():
    # 动态导入包和函数
    module_name, function_name = function_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    route = config['route']
    methods = config['methods']
    # 将函数注册到 Flask 路由
    app.add_url_rule(route, function_name, function, methods=methods)

import argparse
if __name__ == "__main__":
    start_sw()
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="host name")
    parser.add_argument("--port", type=int, default=10051, help="port number")
    args = parser.parse_args()

    app.run(host=args.host, port=int(args.port))
