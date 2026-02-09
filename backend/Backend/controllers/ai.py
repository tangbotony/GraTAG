import json
from http import HTTPStatus

from config import llm_log, config_manager
from controllers import UNKNOW
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
import requests
from webargs import fields
from webargs.flaskparser import use_args

router_ai = Blueprint('ai', __name__)
algorithm_url = config_manager.default_config['ALGORITHM_2_URL']
headers = {
        "token":"20548cb5a329260ead027437cb22590e945504abd419e2e44ba312feda2ff29e",
        "language": "zh-CN"
        }
# 基础扩写
@router_ai.route('/api/ai/basic_expand_write', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
          "context_above": fields.Str(), "context_below": fields.Str(), "output_num": fields.Int(), "page_title": fields.Str(),
           "output_length_rate": fields.Float()}, location="json", unknown=UNKNOW)
def basic_expand_write(data):
    res = None
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_expand_write",
        "url":"/api/ai/basic_expand_write",
        "msg":"basic expand write data: {}".format(json.dumps(data, ensure_ascii=False))
    }, ensure_ascii=False))
    try:

        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = algorithm.basic_expand_write(**data)
        url = algorithm_url + "/basic_expand_write"
        res = requests.request("POST", url, headers=dynamic_headers, json=data) 
        results = json.loads(res.content)

    except Exception as e:
        return jsonify({'result': None, 'message': "基础扩写接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_expand_write",
        "url":"/api/ai/basic_expand_write",
        "msg":"basic expand write data: {}".format(json.dumps(results, ensure_ascii=False))
    }, ensure_ascii=False))
    return jsonify({'result': results, 'message': ''}), HTTPStatus.OK


# 基础续写
@router_ai.route('/api/ai/basic_continue_write', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
           "context_above": fields.Str(), "context_below": fields.Str(), "output_num": fields.Int(), "page_title": fields.Str(),
          "output_length_rate": fields.Float()}, location="json", unknown=UNKNOW)
def basic_continue_write(data):
    res = None
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_continue_write",
        "url":"/api/ai/basic_continue_write",
        "msg":"basic continue write data: {}".format(json.dumps(data, ensure_ascii=False))
    }, ensure_ascii=False))
    try:

        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = algorithm.basic_continue_write(**data)
        url = algorithm_url + "/basic_continue_write"
        res = requests.request("POST", url, headers=dynamic_headers, json=data) 
        results = json.loads(res.content)

    except Exception as e:
        return jsonify({'result': None, 'message': "基础续写接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_continue_write",
        "url":"/api/ai/basic_continue_write",
        "msg":"basic polish write data: {}".format(json.dumps(results, ensure_ascii=False))
    }, ensure_ascii=False))
    return jsonify({'result': results, 'message': ''}), HTTPStatus.OK


# 基础润色
@router_ai.route('/api/ai/basic_polish_write', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
           "context_above": fields.Str(), "context_below": fields.Str(), "output_num": fields.Int(), "page_title": fields.Str(),
          "polish_type": fields.Str(),"style": fields.Str()}, location="json", unknown=UNKNOW)
def basic_polish_write(data):
    res = None
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_polish_write",
        "url":"/api/ai/basic_polish_write",
        "msg":"basic polish write data: {}".format(json.dumps(data, ensure_ascii=False))
    }, ensure_ascii=False))
    try:
        
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = algorithm.basic_polish_write(**data)
        url = algorithm_url + "/basic_polish_write"
        res = requests.request("POST", url, headers=dynamic_headers, json=data) 
        results = json.loads(res.content)

    except Exception as e:
        return jsonify({'result': None, 'message': "基础润色接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_polish_write",
        "url":"/api/ai/basic_polish_write",
        "msg":"basic polish write data: {}".format(json.dumps(results, ensure_ascii=False))
    }, ensure_ascii=False))
    return jsonify({'result': results, 'message': ''}), HTTPStatus.OK


# 专业续写
@router_ai.route('/api/ai/pro_continue_write', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
           "context_above": fields.Str(), "context_below": fields.Str(), "output_num": fields.Int(), "page_title": fields.Str(),
          "pro_setting_length": fields.Float(), "pro_setting_continue_direction": fields.Dict(),
          "pro_setting_special_request": fields.Str(), "pro_setting_language_type": fields.Str()}, location="json", unknown=UNKNOW)
def pro_continue_write(data):
    res = None
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"pro_continue_write",
        "url":"/api/ai/pro_continue_write",
        "msg":"pro continue write data: {}".format(json.dumps(data, ensure_ascii=False))
    }, ensure_ascii=False))
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = algorithm.pro_continue_write(**data)
        url = algorithm_url + "/pro_continue_write"
        res = requests.request("POST", url, headers=dynamic_headers, json=data) 
        results = json.loads(res.content)
        
    except Exception as e:
        return jsonify({'result': None, 'message': "专业续写接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"pro_continue_write",
        "url":"/api/ai/pro_continue_write",
        "msg":"pro continue write data: {}".format(json.dumps(results, ensure_ascii=False))
    }, ensure_ascii=False))
    return jsonify({'result': results, 'message': ''}), HTTPStatus.OK

# 引证基础续写
@router_ai.route('/api/ai/basic_continue_write_reference', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
           "context_above": fields.Str(), "context_below": fields.Str(), "output_num": fields.Int(), "page_title": fields.Str(),
          "output_length_rate": fields.Float()}, location="json", unknown=UNKNOW)
def basic_continue_write_reference(data):
    res = None
    try_num = 2
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_continue_write_reference",
        "url":"/api/ai/basic_continue_write_reference",
        "msg":"basic reference continue write data: {}".format(json.dumps(data, ensure_ascii=False))
    }, ensure_ascii=False))
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language
        while try_num:
            try_num -= 1

            # res = algorithm.basic_continue_write_reference(**data)
            url = algorithm_url + "/basic_continue_write_reference"
            res = requests.request("POST", url, headers=dynamic_headers, json=data) 
            results = json.loads(res.content)

            if res:
                break
    except Exception as e:
        return jsonify({'result': None, 'message': "引证基础续写接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"basic_continue_write_reference",
        "url":"/api/ai/basic_continue_write_reference",
        "msg":"basic reference continue write data: {}".format(json.dumps(results, ensure_ascii=False))
    }, ensure_ascii=False))
    return jsonify({'result': results, 'message': ''}), HTTPStatus.OK

# 引证专业续写
@router_ai.route('/api/ai/pro_continue_write_reference', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
           "context_above": fields.Str(), "context_below": fields.Str(), "output_num": fields.Int(), "page_title": fields.Str(),
          "pro_setting_length": fields.Float(), "pro_setting_continue_direction": fields.Dict(),
          "pro_setting_special_request": fields.Str(), "pro_setting_language_type": fields.Str()}, location="json", unknown=UNKNOW)
def pro_continue_write_reference(data):
    res = None
    try_num = 2
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"pro_continue_write_reference",
        "url":"/api/ai/pro_continue_write_reference",
        "msg":"pro reference continue write data: {}".format(json.dumps(data, ensure_ascii=False))
    }, ensure_ascii=False))
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language
        while try_num:
            try_num -= 1

            # res = algorithm.pro_continue_write_reference(**data)
            url = algorithm_url + "/pro_continue_write_reference"
            res = requests.request("POST", url, headers=dynamic_headers, json=data) 
            results = json.loads(res.content)
     
            if res:
                break
    except Exception as e:
        return jsonify({'result': None, 'message': "引证专业续写接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"pro_continue_write_reference",
        "url":"/api/ai/pro_continue_write_reference",
        "msg":"pro reference continue write data: {}".format(json.dumps(results, ensure_ascii=False))
    }, ensure_ascii=False))
    return jsonify({'result': results, 'message': ''}), HTTPStatus.OK

# 引证
@router_ai.route('/api/ai/ai_reference_check', methods=['POST'])
@jwt_required()
@use_args({"selected_content": fields.Str(required=True), "doc_id": fields.Str(required=True),
           "context_above": fields.Str(), "context_below": fields.Str()}, location="json")
def ai_reference_check(data):
    params = {}
    for key in data:
        params[key] = data[key]
    params.pop("doc_id")

    language = request.headers.get("language", "zh-CN")
    dynamic_headers = headers.copy()
    dynamic_headers['language'] = language

    # res = algorithm.ai_reference_check(**params)
    url = algorithm_url + "/ai_reference_check"
    res = requests.request("POST", url, headers=dynamic_headers, json=params) 
    results = json.loads(res.content)

    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"ai_reference_check",
        "url":"/api/ai/ai_reference_check",
        "msg":f"reference_check_data:{json.dumps(results, ensure_ascii=False)}"
    }, ensure_ascii=False))
    return jsonify({'result': results}), HTTPStatus.OK

# title生成
@router_ai.route('/api/ai/basic_article2title', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True),"selected_content": fields.Str(required=True), "output_length": fields.Int(),
           "min_output_length": fields.Int(), "max_output_length": fields.Int(), "output_num": fields.Int(),"style": fields.Str()}, location="json", unknown=UNKNOW)
def basic_article2title(data):
    params = {}
    for key in data:
        params[key] = data[key]
    try:

        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = algorithm.basic_article2title(**params)
        url = algorithm_url + "/basic_article2title"
        res = requests.request("POST", url, headers=dynamic_headers, json=params) 
        results = json.loads(res.content)

    except Exception as e:
        return jsonify({'result': None, 'message': "title生成接口调用失败： " + str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    # data["res"], data['action'] = res, request.path
    llm_log.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":"",
        "module":"ai_reference_check",
        "url":"/api/ai/ai_reference_check",
        "msg":f"reference_check_data:{json.dumps(results, ensure_ascii=False)}"
    }, ensure_ascii=False))
    return jsonify({'result': results}), HTTPStatus.OK
