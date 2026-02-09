import datetime
import json
import os
from http import HTTPStatus

import jwt as j
from config import config_manager, default_log, monitor_log, response_log
from controllers.admin import router_admin
from controllers.ai import router_ai
from controllers.document import router_document
from controllers.event_tracking import router_event_tracking
from controllers.feedback import router_feedback
from controllers.folder import router_folder
from controllers.trash import router_trash
from controllers.user import route_user
from controllers.comment_news import router_ai_comment
from controllers.qa import router_qa
from controllers.material import router_material
from controllers.material_news import router_ai_material
from flask import Flask, jsonify, request, g, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, jwt_required, verify_jwt_in_request, get_jwt_header
from flask_mongoengine import MongoEngine
import logging
import time
import requests
import threading
import pymongo
from prometheus_flask_exporter import PrometheusMetrics
from models.user import User
from models.login_history import LoginHistory


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 增加file logger hanlder
app.logger.addHandler(default_log)
app.logger.setLevel(logging.INFO)
monitor_logger=monitor_log

# 配置mongodb
app.config['MONGODB_SETTINGS'] = {
    'db':   config_manager.mongo_config['DB'],
    'host': config_manager.mongo_config['Host'],
    'port': int(config_manager.mongo_config['Port']),
    'username': config_manager.mongo_config['Username'],
    'password': config_manager.mongo_config['Password'],
    'authentication_source': config_manager.mongo_config['authDB']
}
db = MongoEngine(app)

# 配置跨域
cors = CORS(app, resources={r"*": {"origins": "*"}}, 
            allow_headers="*",
    supports_credentials=True,
)

# 注册Flask监控
if config_manager.prometheus_config['enable_flask'] == 'True':
    PrometheusMetrics(app)

# 注册路由
app.register_blueprint(route_user)
app.register_blueprint(router_document)
app.register_blueprint(router_folder)
app.register_blueprint(router_trash)
app.register_blueprint(router_ai)
app.register_blueprint(router_feedback)
app.register_blueprint(router_admin)
app.register_blueprint(router_event_tracking)
app.register_blueprint(router_ai_comment)
app.register_blueprint(router_qa)
app.register_blueprint(router_material)
app.register_blueprint(router_ai_material)


#注册jwt
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = config_manager.default_config['TOKEN_KEY']  # token密钥
app.config['JWT_BLACKLIST_ENABLED'] = True  # 黑名单管理
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']  # 允许将access and refresh tokens加入黑名单
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=30)

def send_monitor_request(data):
    pass

# 捕获422和400的异常码
@app.errorhandler(422) 
@app.errorhandler(400)
def handle_error(err):
    messages = err.data.get("messages", ["Invalid request."])
    return jsonify({'message': messages}), HTTPStatus.BAD_REQUEST

@jwt_required(optional=True)
@app.before_request
def before_request():
    g.st = time.time()
    g.user_name = ""
    req_body = request.get_data(as_text=True)
    monitor_logger.logger.info(json.dumps({"message": f'get one request. req_path: {request.path}, req_body: {req_body}'}))
    if request.path == '/api/login' and request.method.lower() == "post":
        g.user_name = request.get_json().get("name", "")
    if request.path == '/api/heartbeat': return
    if request.path == '/api/refresh': return
    if request.path != '/api/login' and request.path != '/api/logout_batch' and request.path != '/api/event' and "/api/image" not in request.path and request.path != '/metrics':
        if verify_jwt_in_request():
            user_id = get_jwt_identity()
            super_user = User.objects(_id=user_id).first()

            # 校验登录状态, 是否被踢登, 或者超时
            auth_header = request.headers.get('Authorization')
            is_login = LoginHistory.objects(access_token=auth_header[7:], status=1, expire_time__gt=datetime.datetime.now()).first()
            if not is_login:
                monitor_logger.logger.error(json.dumps({"error": f'The login status is invalid. Please log in again(>_<). user_id: {user_id}, user_name: {super_user.name}'}))
                return jsonify({'res': "", 'message': "登录状态失效, 请重新登录(>_<)"}), HTTPStatus.REQUEST_TIMEOUT

            # 登录状态有效, 更新登录失效时间
            (LoginHistory.objects(access_token=auth_header[7:], status=1, expire_time__gt=datetime.datetime.now())
             .update(set__expire_time=datetime.datetime.now() + datetime.timedelta(days=7)))

            # 校验试用期
            create_date = super_user.create_date
            expire_date = super_user.expire_date
            today_date = datetime.datetime.today()
            if create_date:
                create_date = datetime.datetime.strptime(create_date, "%Y-%m-%d")
                if create_date > today_date:
                    monitor_logger.logger.error(json.dumps(
                        {"error": f"Your trial has not started yet, please contact your administrator！user_id: {user_id}, user_name: {super_user.name}"}))
                    return jsonify({'res':"", 'err': "您的试用还未开始，请联系管理员处理！"}), HTTPStatus.UNAUTHORIZED

            if expire_date:
                expire_date = datetime.datetime.strptime(expire_date, "%Y-%m-%d") + datetime.timedelta(days=1)
                if expire_date < today_date:
                    monitor_logger.logger.error(json.dumps(
                        {"error": f"Your trial has expired. Please contact your administrator！user_id: {user_id}, user_name: {super_user.name}"}))
                    return jsonify({'res':"", 'err': "您的试用已到期，请联系管理员处理！"}), HTTPStatus.UNAUTHORIZED
            
            # 若为admin相关操作，则需要检验权限
            if 'admin' in request.path:
                access_type = super_user.access_type
                if access_type == 'normal':
                    monitor_logger.logger.error(json.dumps(
                        {"error": f"Your account does not have permission to do this！user_id: {user_id}, user_name: {super_user.name}"}))
                    return jsonify({'res':"", 'err': "您的账号没有此操作的权限！"}), HTTPStatus.UNAUTHORIZED

# 打印请求记录
@app.after_request
def after_request(response):

    user_id, user_name, request_id = "", "", ""
    try:
        auth = request.headers.get('Authorization')
        if auth and auth.startswith('Bearer '):
            "提取token 0-6 被Bearer和空格占用 取下标7以后的所有字符"
            token = auth[7:]
            payload = j.decode(token, config_manager.default_config['TOKEN_KEY'], algorithms=['HS256'])
            user_name = payload.get('user_name')
            user_id = payload.get('user_id')
        
        request_id = request.headers.get('x-request-id', "")

        if request.method.lower() == "post" and request.is_json and request_id == "":
            request_id = request.get_json().get("request_id", "")
    except Exception as e:
        monitor_logger.logger.error(json.dumps({"request_id":request_id,"error":str(e)}))

    if g.user_name:
        user_name = g.user_name

    try:
        request_data = {
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers),
            "body": request.get_data(as_text=True)  # 获取请求体
        }
        
        if request.path not in ['/api/qa/ask','/api/material/upload','/api/doc_search/upload']  and 'metrics' not in request.path:

            response_body = response.get_data(as_text=True)  # 获取响应体的原始字符串
            try:
                response_body = json.loads(response_body)  # 尝试解析为 JSON
            except json.JSONDecodeError:
                pass  # 如果解析失败，保留原始字符串
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body  # 获取响应体
            }
            
            response_log.logger.info(json.dumps(
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "method": request.method,
                    "ip": request.headers.get('X-Real-IP', request.remote_addr),
                    "url": request.path,
                    "rt": time.time() - g.st,
                    "request": request_data,
                    "response": response_data
                }, ensure_ascii=False)
            )
    except Exception as e:
        monitor_logger.logger.error(json.dumps({"request_id":request_id,"error":str(e)}))

    
    monitor_logger.logger.info(json.dumps({
            "user_id": user_id,
            "user_name": user_name,
            "request_id": request_id,
            "status_code": response.status_code,
            "method": request.method,
            "ip": request.headers.get('X-Real-IP', request.remote_addr),
            "url": request.path,
            "rt": time.time() - g.st
        }, ensure_ascii=False
    ))
    response.headers.add('Access-Control-Allow-Headers', '*')
    return response

# 心跳接口
@app.route('/api/heartbeat', methods=['GET'])
def heartbeat():
    return jsonify({'status': "1"}), HTTPStatus.OK

# @app.errorhandler(Exception)
# def framework_error(e):
#     app.logger.error("error info: %s" % e) # 对错误进行日志记录
#     data = {
#         "code": -1,
#         "msg": str(e),
#     }
#     return jsonify(data), HTTPStatus.INTERNAL_SERVER_ERROR
# mong_db = mongo_client.llm
# collection = mong_db['result']
# def save_context_into_mongo(request_id, event_id, context):
#     try:
#         mongo_res = collection.update_one({"_id": request_id}, {"$set": {"_id": request_id, "context": context}}, upsert=True)
#     except Exception as e:
#         monitor_logger.logger.error(json.dumps({"request id": request_id, "event id": event_id, "error" :str(e)}))


