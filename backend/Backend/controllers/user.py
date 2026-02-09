import datetime
from http import HTTPStatus
import json

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                get_jti, get_jwt, get_jwt_identity,
                                jwt_required, get_jwt_header)
from models.jwt import BlackToken
from models.user import User
from models.login_history import LoginHistory
from webargs import fields
from webargs.flaskparser import use_args

from config import monitor_log

route_user = Blueprint('user', __name__)

monitor_logger=monitor_log

# 查询用户信息
@route_user.route('/api/user', methods=['GET'])
@jwt_required()
def get_user():
    id = get_jwt_identity()
    user = User.objects(_id=id).first()
    if not user:
        return jsonify({'message': "not find user with id: {}".format(id)}), HTTPStatus.UNAUTHORIZED
    return jsonify({'message': "", 'userinfo': user}), HTTPStatus.OK
        
    
# 更新用户信息
# TODO
@route_user.route('/api/user/<id>', methods=['POST'])
@jwt_required()
def update_user(id):
    jwt_id = get_jwt_identity()
    if id != jwt_id:
        return jsonify({'message': "conflict between input id {} and jwt id: {}".format(id, jwt_id)}), HTTPStatus.BAD_REQUEST
    data = request.get_json()
    extend_data = {"extend_data": data.get('extend_data', {})}

    user = User.objects(_id=id).first()
    if not user:
        return jsonify({'message': "not find user with id: {}".format(id)}), HTTPStatus.BAD_REQUEST
    status = user.update(**extend_data)
    return jsonify({'message': "", 'status': status}), HTTPStatus.OK


# 登陆账号
@route_user.route('/api/login', methods=['POST'])
@use_args({"name": fields.Str(required=True), "passwd": fields.Str(required=True), "force": fields.Str(required=False)}, location="json")
def login(data):
    name, passwd, force = data.get('name'), data.get('passwd'), data.get('force', '')

    user = User.objects(name=name, passwd=passwd).first()
    if not user:
        monitor_logger.logger.error(json.dumps(
            {"error": f"Incorrect account or password, please confirm！user_name: {name}"}))
        return jsonify({'message': "账号或密码错误，请确认！"}), HTTPStatus.UNAUTHORIZED

    # 先生成有效的token备用
    additional_claims = {'user_id': user._id, "user_name": name}
    refresh_token = create_refresh_token(identity=user._id, additional_claims=additional_claims)
    additional_claims = {'refresh_token': refresh_token, 'user_id': user._id, "user_name": name}
    access_token = create_access_token(identity=user._id, fresh=True, additional_claims=additional_claims)

    # 校验试用期
    expire_date = user.expire_date
    create_date = user.create_date
    today_date = datetime.datetime.today()
    if create_date:
        create_date = datetime.datetime.strptime(create_date, "%Y-%m-%d")
        if create_date > today_date:
            monitor_logger.logger.error(json.dumps(
                {"error": f"Your trial has not started yet, please contact your administrator！user_id: {user._id}, user_name: {name}"}))
            return jsonify({'message': "您的试用还未开始，请联系管理员处理！"}), HTTPStatus.UNAUTHORIZED

    if expire_date:
        expire_date = datetime.datetime.strptime(expire_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        if expire_date < today_date:
            monitor_logger.logger.error(json.dumps(
                {"error": f"Your trial has expired. Please contact your administrator！user_id: {user._id}, user_name: {name}"}))
            return jsonify({'message': "您的试用已到期，请联系管理员处理！"}), HTTPStatus.UNAUTHORIZED

    # 校验登录设备数量,需要噶掉几个账户, 用户按登录时间倒叙, 从第max_devices个用户开始, 全部噶掉
    max_devices = user.max_devices
    # 按登录时间倒叙查询所有登录的账号
    login_users = LoginHistory.objects(name=user.name, status=1,
                                       expire_time__gt=datetime.datetime.now()).order_by('-create_time')
    # 若已登录成功的账号不小于限制数, 则说明当前设备若想登录, 则需要噶掉至少一人
    if not (len(login_users) < max_devices):
        last_tokens = [last_user.access_token for last_user in login_users[(max_devices - 1):]]
        if force == 'true':
            for logout_token in last_tokens:
                LoginHistory.objects(access_token=logout_token).update(set__status=0)
        else:
            out_msg = f"只允许同时登录{max_devices}个设备，是否要退出最前面登录的{len(login_users) - max_devices + 1}个设备"
            monitor_logger.logger.error(json.dumps(
                {"error": out_msg}))
            return (jsonify({'res': "", 'message': out_msg,
                             'access_token': access_token, 'refresh_token': refresh_token,
                             'last_tokens': last_tokens}),
                    HTTPStatus.LOCKED)

    # TODO 存储登录信息
    now = datetime.datetime.now()
    LoginHistory(name=name, access_token=access_token, refresh_token=refresh_token, jti=get_jti(refresh_token), status=1, create_time=now,
                 expire_time=now + datetime.timedelta(days=7)).save()


    current_app.logger.info(json.dumps({
        "request_id":"",
        "event_id":"",
        "module":"user",
        "url":"/api/login",
        "msg":"login success with user id: {}, user name: {}".format(name, user._id)
    }, ensure_ascii=False))
    return {'access_token': access_token, 'refresh_token': refresh_token}, HTTPStatus.OK


# 退出账号
@route_user.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    # now = datetime.datetime.now() + datetime.timedelta(days=1)
    # token = get_jwt()
    access_token = request.headers.get('Authorization')[7:]
    LoginHistory.objects(access_token=access_token).update(set__status=0)
    # jti = token["jti"]
    # ttype = token["type"]
    # black_token = BlackToken(jti=jti, type=ttype, expireAt=now).save()
    #
    # # revoke refresh token
    # refresh_token = token["refresh_token"]
    # jti_refresh_token = get_jti(refresh_token)
    # ttype = "refresh"
    # refresh_black_token = BlackToken(jti=jti_refresh_token, type=ttype, expireAt=now).save()

    return {"message": "Logout successfully"}, HTTPStatus.OK


# 退出账号
@route_user.route('/api/logout_batch', methods=['POST'])
# @jwt_required()
@use_args({"logout_tokens": fields.List(fields.Str(), required=True)}, location="json")
def logout_batch(data):
    # TODO 更新登录信息, 不能用$in, 防止logout_tokens, 导致全体下线
    logout_tokens = data.get('logout_tokens', [])
    for logout_token in logout_tokens:
        LoginHistory.objects(access_token=logout_token).update(set__status=0)

    return {"message": "Logout successfully"}, HTTPStatus.OK

# 刷新jwt token
@route_user.route('/api/refresh', methods=['GET'])
@jwt_required(refresh=True)
def refresh_token():
    # 判断refresh是否已被删除
    refresh_token = get_jwt()
    jti_refresh_token = refresh_token["jti"]
    black_token = BlackToken.objects(jti=jti_refresh_token).first()
    if black_token:
        return {'message': "refresh token is envoke"}, HTTPStatus.UNAUTHORIZED
    
    refresh_token_string = request.headers.get("Authorization").replace("Bearer ", "")
    current_user = get_jwt_identity()
    additional_claims = {'refresh_token': refresh_token_string, 'user_id': refresh_token['user_id'], 'user_name': refresh_token['user_name']}
    new_token = create_access_token(identity=current_user, fresh=True, additional_claims=additional_claims)
    return {'access_token': new_token}, HTTPStatus.OK

