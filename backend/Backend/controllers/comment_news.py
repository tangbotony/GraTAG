from http import HTTPStatus

from controllers import UNKNOW, es_client
from flask import Blueprint, jsonify, current_app, request
from config import llm_log, config_manager
from flask_jwt_extended import jwt_required, get_jwt_identity
from webargs import fields
from webargs.flaskparser import use_args
import datetime
import sys
import copy
import concurrent.futures
import os
import json
import difflib
import pymongo
import traceback
import pickle
from controllers.utils import query_network

path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(path, "/doc_based_alg/review_article_gen/online_version/generate_review"))

import requests

router_ai_comment = Blueprint('ai_comment', __name__)

mongo_client = pymongo.MongoClient(host=config_manager.mongo_config['Host'], port=int(config_manager.mongo_config['Port']), 
                                   username=config_manager.mongo_config['Username'], password=config_manager.mongo_config['Password'], authSource=config_manager.mongo_config['authDB'])
mong_db = mongo_client.llm
collection = mong_db['context']

algorithm_url = config_manager.default_config['ALGORITHM_2_URL']
headers = {
        "token":"20548cb5a329260ead027437cb22590e945504abd419e2e44ba312feda2ff29e"
        }

@router_ai_comment.route('/api/ai/comment/generate_recent_event', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=False)}, location="json", unknown=UNKNOW)
def generate_recent_event(data):
    """
    获取一个最近发生的热点事件

    Returns: 返回选中事件的描述，论点和论据
    """

    path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    final_path = os.path.join(path, 'config/Shading.json')
    with open(final_path, encoding="utf-8") as file:
        data = json.loads(file.read())
    res = {"event_desc": "例如：" + data.get('event'), "event_argument": "例如：" + data.get('argument'), "event_evidence": "例如：" + data.get('evidence')}
    return jsonify({'result': res, 'message': ''}), HTTPStatus.OK


@router_ai_comment.route('/api/ai/comment/generate_search', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=True), "search": fields.Str(required=True)}, location="json", unknown=UNKNOW)
def search_event(data):
    """
    根据搜索词条检索对应的事件
    :search: 搜索词条按

    Returns: 返回多条搜索的事件，包含事件 title 和摘要
    """
    
    result = None
    try:
        result, err = query_network(raw_text=data.get("search"))

        if err != None or not result:
            current_app.logger.error(json.dumps({
                "request_id":data.get("request_id"),
                "event_id":data.get("event_id"),
                "module":"comment_article",
                "url":"/api/ai/comment/generate_search",
                "msg":"get baidu event failed for err {}".format(str(err))
            }, ensure_ascii=False))
            return jsonify({'result': '', 'message': "not found available event"}), HTTPStatus.OK
        # data_lists = res.get("hits").get("hits")
    except Exception as e:
        current_app.logger.error(json.dumps({
            "request_id":data.get("request_id"),
            "event_id":data.get("event_id"),
            "module":"comment_article",
            "url":"/api/ai/comment/generate_search",
            "msg":"get baidu event failed for err {}".format(str(e))
            }, ensure_ascii=False))
        return jsonify({'result': '', 'message': "not found available event"}), HTTPStatus.OK
    
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_search",
        "msg":f"get event num: {len(result)}"
    }, ensure_ascii=False))
    
    res = []
    for item in result:
        title, abstract, url = item.get('title'), item.get('description'), item.get('url')
        if title and abstract:
            res.append({"title": title, "abstract": abstract, "url": url})
    
    return jsonify({'result': res, 'message': ''}), HTTPStatus.OK


@router_ai_comment.route('/api/ai/comment/generate_general_argument', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=True), 
           "event": fields.Str(required=True), "title": fields.Str(required=True), "abstract": fields.Str(required=True),
           "require": fields.Str(required=False), "arguments": fields.List(cls_or_instance=fields.Dict(), required=False)}, location="json", unknown=UNKNOW)
def generate_general_argument(data):
    """
    根据事件生成总论点
    :event: 用户输入
    :title: 用户选择事件的标题
    :abstract: 用户选择事件的摘要
    :require: 用户选择重新生成的要求
    :arguments: 用户选择的论点论据

    Returns: 返回多条总论点
    """
    user_id = get_jwt_identity()
    data["user_id"] = user_id

    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_general_argument",
        "msg":f"generate general argument context input: {data}"
    }, ensure_ascii=False))
    
    res = ""
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = generate_major_point(context)
        url = algorithm_url + "/generate_general_argument"
        res = requests.request("POST", url, headers=dynamic_headers, json=data ) 
        results = json.loads(res.content)

    except Exception as e:
        current_app.logger.error(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_general_argument",
        "msg":"generate major point failed for err {}".format(str(e))
    }, ensure_ascii=False))
        return jsonify({'result': "", 'message': "全文生成摘要接口调用失败： {}".format(str(e))}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_general_argument",
        "msg":f"generate general argument context output: {results}"
    }, ensure_ascii=False))
    return jsonify({'result': results}), HTTPStatus.OK


@router_ai_comment.route('/api/ai/comment/generate_argument_evidence', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=True), 
           "event": fields.Str(required=True), "title": fields.Str(required=True), "abstract": fields.Str(required=True),
           "require": fields.Str(required=False), "structrue": fields.Str(required=True), 
           "arguments": fields.List(cls_or_instance=fields.Dict(), required=False),
           "generate_arguments": fields.Dict(required=False), "generalArgument": fields.Str(required=True), 
           "generalArgumentFix": fields.Str(required=True)}, location="json", unknown=UNKNOW)
def generate_argument_evidence(data):
    """
    根据总论点生成论点论据
    :event: 用户输入
    :title: 用户选择事件的标题
    :abstract: 用户选择事件的摘要
    :requeire: 用户选择重新生成的要求
    :arguments: 用户选择的论点论据
    :structrue: 论述结构
    :generalArgument: 生成的总论点
    :generalArgumentFix: 修改后的总论点
    :generate_arguments: 之前生成的论点论据
        :argument: 论点
        :evidence: 论据
        :status: 状态，是否勾选
        :page: 页码

    Returns: 返回论点论据
    """
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_argument_evidence",
        "msg":f"generate argument context input: {data}"
    }, ensure_ascii=False))

    res = ""
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = generate_sub_opinion(context)
        url = algorithm_url + "/generate_argument_evidence"
        res = requests.request("POST", url, headers=dynamic_headers, json=data ) 
        results = json.loads(res.content)
    except Exception as e:
        current_app.logger.error(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_argument_evidence",
        "msg":"generate sub opinion failed for err {}".format(str(e))
    }, ensure_ascii=False))
        return jsonify({'result': "", 'message': "全文生成论点生成接口失败： {}".format(str(e))}), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_argument_evidence",
        "msg":"res:" + str(res)
    }, ensure_ascii=False))
    return jsonify({'result': results}), HTTPStatus.OK


@router_ai_comment.route('/api/ai/comment/generate_evidence', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=True), 
           "event": fields.Str(required=True), "title": fields.Str(required=True), "abstract": fields.Str(required=True),
           "require": fields.Str(required=False), "structrue": fields.Str(required=True), 
           "arguments": fields.List(cls_or_instance=fields.Dict(), required=False),
           "generate_arguments": fields.Dict(required=False), "generalArgument": fields.Str(required=True), 
           "generalArgumentFix": fields.Str(required=True), "currentArgument": fields.Dict(required=True)}, location="json", unknown=UNKNOW)
def get_evidence(data):
    """
    根据总论点生成论点论据
    :event: 用户输入
    :title: 用户选择事件的标题
    :abstract: 用户选择事件的摘要
    :requeire: 用户选择重新生成的要求
    :arguments: 用户选择的论点论据
    :structrue: 论述结构
    :generalArgument: 生成的总论点
    :generalArgumentFix: 修改后的总论点
    :generate_arguments: 之前生成的论点论据
        :argument: 论点
        :evidence: 论据
        :status: 状态，是否勾选
        :page: 页码
    :current_argument: 当前论点

    Returns: 返回论点论据
    """

    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_evidence",
        "msg":"======current_opinion_index: {}, current_page: {}========".
                            format(data.get('currentArgument', {}).get('index', 'sub_opinion_1'), data.get('current_page'))
    }, ensure_ascii=False))
    

    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_evidence",
        "msg":f"generate evidence context input: {data}"
    }, ensure_ascii=False))

    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = generate_evidence(context)
        url = algorithm_url + "/generate_evidence"
        res = requests.request("POST", url, headers=dynamic_headers, json=data ) 
        results = res.text

    except Exception as e:
        current_app.logger.error(json.dumps({
    "request_id":data.get("request_id"),
    "event_id":data.get("event_id"),
    "module":"comment_article",
    "url":"/api/ai/comment/generate_evidence",
    "msg":"generate evidence failed for err {}".format(str(e))
}, ensure_ascii=False))

    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_evidence",
        "msg":f"generate evidence context output: {results}"
    }, ensure_ascii=False))
    return jsonify({'result': results}), HTTPStatus.OK


@router_ai_comment.route('/api/ai/comment/generate_article', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=True), 
           "event": fields.Str(required=True), "title": fields.Str(required=True), "abstract": fields.Str(required=True),
           "require": fields.Str(required=False), "structrue": fields.Str(required=True), 
           "arguments": fields.List(cls_or_instance=fields.Dict(), required=False),
           "generate_arguments": fields.Dict(required=False), "generalArgument": fields.Str(required=True), 
           "generalArgumentFix": fields.Str(required=True), "title_word_count": fields.Int(required=False),
           "article_type": fields.Str(required=False)}, location="json", unknown=UNKNOW)
def generate_article(data):
    """
    根据论点论据生成全文
    :event: 用户输入
    :title: 用户选择事件的标题
    :abstract: 用户选择事件的摘要
    :requeire: 用户选择重新生成的要求
    :arguments: 用户选择的论点论据
    :structrue: 论述结构
    :generalArgument: 生成的总论点
    :generalArgumentFix: 修改后的总论点
    :generate_arguments: 之前生成的论点论据
        :argument: 论点
        :evidence: 论据
        :status: 状态，是否勾选
        :page: 页码
    :title_word_count: title 的长度
    :atricle_type: 文章类型

    Returns: 返回title 和 content
    """

    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_article",
        "msg":f"generate article context input: {data}"
    }, ensure_ascii=False))
    
    res = ""
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        url = algorithm_url + "/generate_article"
        res = requests.request("POST", url, headers=dynamic_headers, json=data ) 
        results = json.loads(res.content)
    except Exception as e:
        current_app.logger.error(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_article",
        "msg":"generate review article failed for err {}".format(str(e))
    }, ensure_ascii=False))
        return jsonify({'result': "", 'message': "全文生成接口失败： {}".format(str(e))}), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_article",
        "msg":f"generate article context output: {results}"
    }, ensure_ascii=False))
    return jsonify({'result': results['result']}), HTTPStatus.OK
    
    # 调用唐波接口
    pass

@router_ai_comment.route('/api/ai/comment/generate_title', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True), "event_id": fields.Str(required=True), 
           "event": fields.Str(required=True), "title": fields.Str(required=True), "abstract": fields.Str(required=True),
           "require": fields.Str(required=False), "structrue": fields.Str(required=True), 
           "arguments": fields.List(cls_or_instance=fields.Dict(), required=False),
           "generate_arguments": fields.Dict(required=False), "generalArgument": fields.Str(required=True), 
           "generalArgumentFix": fields.Str(required=True), "title_list": fields.List(cls_or_instance=fields.Str(), required=True),
           "context": fields.Str(required=True)}, location="json", unknown=UNKNOW)
def change_title(data):
    """
    根据修改 title
    :event: 用户输入
    :title: 用户选择事件的标题
    :abstract: 用户选择事件的摘要
    :requeire: 用户选择重新生成的要求
    :arguments: 用户选择的论点论据
    :structrue: 论述结构
    :generalArgument: 生成的总论点
    :generalArgumentFix: 修改后的总论点
    :generate_arguments: 之前生成的论点论据
        :argument: 论点
        :evidence: 论据
        :status: 状态，是否勾选
        :page: 页码
    :title_lists: 过去生成的 title lists
    :content: 当前文章

    Returns: 返回title
    """
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_title",
        "msg":f"generate title context input: {data}"
    }, ensure_ascii=False))

    res = ""
    try:
        language = request.headers.get("language", "zh-CN")
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = language

        # res = generate_title(context)
        url = algorithm_url + "/generate_title"
        res = requests.request("POST", url, headers=dynamic_headers, json=data ) 
        results = res.text
    except Exception as e:
        current_app.logger.error(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_title",
        "msg":"generate title failed for err {}".format(str(e))
    }, ensure_ascii=False))
        return jsonify({'result': "", 'message': "标题生成接口失败：{}".format(str(e))}), HTTPStatus.INTERNAL_SERVER_ERROR
    # if res.get("code") != ReturnCode.FUNCTION_RUN_SUCCESS:
    #     return jsonify({'result': "", "message": "标题生成接口失败：" + str(res.get("msg"))}), HTTPStatus.INTERNAL_SERVER_ERROR
    # res = context.get_title()
    current_app.logger.info(json.dumps({
        "request_id":data.get("request_id"),
        "event_id":data.get("event_id"),
        "module":"comment_article",
        "url":"/api/ai/comment/generate_title",
        "msg":f"generate title context output: {results}"
    }, ensure_ascii=False))
    return jsonify({'result': results}), HTTPStatus.OK
    


if __name__ == "__main__":
    print(generate_recent_event())



