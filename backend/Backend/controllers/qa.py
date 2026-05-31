import json
from http import HTTPStatus
from config import llm_log, config_manager, response_log
from controllers import UNKNOW
from flask import Blueprint, jsonify, request, Response, stream_with_context, send_from_directory, make_response, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from webargs import fields
from webargs.flaskparser import use_args, use_kwargs
from marshmallow import Schema, fields
from models.qa import Qa_series, Qa_pair_collection, Qa_pair, Subscription, Timeline, Qa_pair_info
from models.upload_file import UploadDocument
import uuid
from datetime import datetime
import requests
import logging
import copy
import tldextract
import traceback
from controllers import (ALLOWED_EXTENSIONS, ALLOWED_IMAGE, IMAGE_URL,
                         UPLOAD_FILE_DIR)
import os
from werkzeug.utils import secure_filename
import shutil
from material.opt_oss import read_material_from_oss, delete_material_from_oss, read_material_from_oss_v2

import threading
import queue

router_qa = Blueprint('qa', __name__)
algorithm_url = config_manager.default_config['ALGORITHM_URL']
headers = {
    "Content-Type":"application/json"
}

# 配置日志记录器
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AlgorithmRequests')
logger.setLevel(logging.INFO)

# 获取当前时间并格式化为指定格式
current_time = datetime.now().strftime("%Y%m%d%H%M%S")

log_file = config_manager.default_config['LOG_DIR'] + 'qa_requests_' + current_time + '.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

SEARCH_MODES = ["pro", "lite", "doc", "doc_pro"]

# 3.1 获得搜索历史记录
@router_qa.route('/api/qa/search/history', methods=['GET'])
@jwt_required()
def get_search_history():
    err_msg = dict()
    user_id = get_jwt_identity()
    history = Qa_series.objects(user_id=user_id, is_search_delete=False).order_by('-create_time').limit(1000)
    history_list = []
    if not history:
        err_msg["error"] = "数据库中未有您的搜索历史记录"
        return jsonify({'err_msg': err_msg, 'results': history_list}), HTTPStatus.OK
    
    latest_history = {}
    for his in history:
        if his.title:
            his_dict = {
                "_id": his._id,
                "title": his.title,
                "create_time": his.create_time
            }
            if his.title not in latest_history or his.create_time > latest_history[his.title]["create_time"]:
                latest_history[his.title] = his_dict
    history_list = list(latest_history.values())
    return jsonify({'err_msg': err_msg, 'results': history_list}), HTTPStatus.OK

# 3.2 清空整个搜索历史记录
@router_qa.route('/api/qa/search/history', methods=['DELETE'])
@jwt_required()
def delete_search_history():
    err_msg = dict()
    user_id = get_jwt_identity()
    history_series = Qa_series.objects(user_id=user_id, is_search_delete=False)
    if not history_series:
        err_msg["error"] = "未在您的历史记录中找到任何搜索记录"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    updated_count = history_series.update(is_search_delete=True) 
    if updated_count == 0:
        err_msg["error"] = "未能清空您的历史记录"
        return jsonify({'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify({'err_msg': err_msg}), HTTPStatus.OK

# 3.3 删除单个历史记录
@router_qa.route('/api/qa/search/history/<id>', methods=['DELETE'])
@jwt_required()
def delete_single_search_history(id):
    err_msg = dict()
    user_id = get_jwt_identity()
    history = Qa_series.objects(user_id=user_id, is_search_delete=False, _id=id).first()
    if not history:
        err_msg["error"] = "未在您的搜索历史记录中找到该记录"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    history.update(is_search_delete=True) 
    return jsonify({'err_msg': err_msg}), HTTPStatus.OK

# 3.4 query 推荐
@router_qa.route('/api/qa/search/completion', methods=['GET'])
@jwt_required()
def get_completion():
    err_msg = dict()
    query = request.args.get('q')
    algorithm_endpoint = f"{algorithm_url}/execute"
    headers = {
    "Content-Type":"application/json"
    }
    try:
        data = {'query': query}
        request_id = request.headers.get('X-Request-Id')
        language = request.headers.get("language", "zh-CN")
        headers['language'] = language
        headers["request-id"] = request_id
        headers["function"] = "recommend_query"
        log_data={}
        log_data["Request_url"] = "recommend_query"
        log_data["Request_headers"] = headers
        log_data["Request_data"] = data
        logger.info(log_data)

        response = requests.post(algorithm_endpoint, json=data, headers=headers)
        log_data={}
        log_data["Response_url"] = "recommend_query"
        log_data["Response_data"] = response.json()
        logger.info(log_data)
        
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get('results')
            return jsonify({'results': results, 'err_msg': err_msg}), HTTPStatus.OK
        else:
            err_msg["error"] = f"Request failed with status code {response.status_code}"
            return {"err_msg": err_msg}, response.status_code
    except requests.RequestException as e:
        err_msg["error"] = f"Request failed: {e}"
        return {"err_msg": err_msg}, HTTPStatus.INTERNAL_SERVER_ERROR

# 3.5 推荐热门问题
@router_qa.route('/api/qa/recommend', methods=['GET'])
@jwt_required()
def recommend_question():
    err_msg = dict()
    headers = {
    "Content-Type":"application/json"
    }
    try:
        url = f"{algorithm_url}/execute"
        headers["function"] = "recommend_question"
        language = request.headers.get("language", "zh-CN")
        headers['language'] = language
        request_id = request.headers.get('X-Request-Id')
        headers["request-id"] = request_id
        
        log_data={}
        log_data["Request_url"] = "recommend_question"
        log_data["Request_headers"] = headers
        logger.info(log_data)

        response = requests.request("POST", url=url, headers=headers)
        log_data={}
        log_data["Response_url"] = "recommend_question"
        log_data["Response_data"] = response.json()
        logger.info(log_data)

        if response.status_code != HTTPStatus.OK:
            err_msg["error"] = "算法接口响应失败！"
            return jsonify({'results': "", 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR
        results = json.loads(response.content)

        if not isinstance(results, dict):
            err_msg["error"] = "算法接口返回格式错误！"
            return jsonify({'results': "", 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        err_msg["error"] = f"推荐热门问题接口异常：{e}"
        return jsonify({'results': results, 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify(results), HTTPStatus.OK

# 3.6 问答历史查询
@router_qa.route('/api/qa/history', methods=['GET'])
@jwt_required()
def get_qa_history():
    err_msg = dict()
    user_id = get_jwt_identity()
    history = Qa_series.objects(user_id=user_id, is_qa_delete=False).order_by('-create_time').limit(1000)
    history_list = []
    if not history:
        err_msg["error"] = "数据库中未有您的问答历史记录"
        return jsonify({'err_msg': err_msg, 'results': history_list}), HTTPStatus.OK
    
    all_pair_ids = []
    for his in history:
        all_pair_ids.extend(his.qa_pair_collection_list)
    
    # 一次性查询所有的Qa_pair_collection对象
    qa_collections = Qa_pair_collection.objects(_id__in=all_pair_ids)
    # 构建一个字典，用于快速查找Qa_pair_collection对象
    qa_collection_map = {pa_c._id: pa_c for pa_c in qa_collections}
    # 构建history_list
    for his in history:
        if his.title:
            his_dict = {}
            his_dict["_id"] = his._id
            his_dict["title"] = his.title
            his_dict["create_time"] = his.create_time
            is_subs = any(qa_collection_map[pair_id].is_subscribed for pair_id in his.qa_pair_collection_list if pair_id in qa_collection_map)        
            his_dict["is_subscribe"] = is_subs
            history_list.append(his_dict)

    return jsonify({'err_msg': err_msg, 'results': history_list}), HTTPStatus.OK

# 3.7 单个问答系列删除
@router_qa.route('/api/qa/series/<qa_series_id>', methods=['DELETE'])
@jwt_required()
def delete_single_series(qa_series_id):
    err_msg = dict()
    user_id = get_jwt_identity()
    history = Qa_series.objects(user_id=user_id, is_qa_delete=False, _id=qa_series_id).first()
    if not history:
        err_msg["error"] = "未在您的问答历史记录中找到该问答记录"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    history.update(is_qa_delete=True) 
    # 加删除对应订阅记录的逻辑
    for pair_id in history.qa_pair_collection_list:
        pa_c = Qa_pair_collection.objects(_id=pair_id).first()
        if pa_c.is_subscribed:
            sub_id = pa_c.subscription_id
            subscription = Subscription.objects(_id=sub_id).first()
            if not subscription:
                err_msg["error"] = "订阅记录删除有误！"
                return jsonify({'status': False,'err_msg': err_msg}), HTTPStatus.NOT_FOUND 
            subscription.delete()
            pa_c.update(is_subscribed = False,subscription_id = "")
    return jsonify({'err_msg': err_msg}), HTTPStatus.OK

# 3.8 单个问答系列详情查询
# 从系列，到问题集合，到问题对所有信息，问题对只要最新的一个即可（页码的最后一个）
@router_qa.route('/api/qa/series/<qa_series_id>', methods=['GET'])
@jwt_required()
def search_series(qa_series_id):
    err_msg = dict()
    user_id = get_jwt_identity()
    # A
    id = qa_series_id
    series = Qa_series.objects(user_id=user_id, is_qa_delete=False, _id=id).first()
    if not series:
        err_msg["error"] = "未在您的问答历史记录中找到该问答记录"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    pair_collection_list = []
    for pair_collection_id in series.qa_pair_collection_list:
        # B
        pa_c = Qa_pair_collection.objects(_id=pair_collection_id).first()
        # is_sub = pa_c.is_subscribed
        # if is_sub:
        #     # D
        #     sub = Subscription.objects(_id=pa_c.subscription_id).first()
        #     # D -> B
        #     pa_c.subscription_id = sub.to_mongo() 
        if not pa_c:
            err_msg["error"] = "该问答系列的问答对集合查找有误"
            return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
        p_id_list = pa_c.qa_pair_list
        if p_id_list:
            latest_id = p_id_list[-1]
            # C
            pair = Qa_pair.objects(_id=latest_id).first()
            if not pair:
                err_msg["error"] = "该问答对集合的问答对查找有误"
                return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
            t_id = pair.timeline_id
            # E
            t = Timeline.objects(_id=t_id).first()
            if t:
            # E -> C
                timeline = t.data
                pair.timeline_id = timeline
            # C -> B
            pa_c.latest_qa_pair = pair.to_mongo()
        pair_collection_list.append(pa_c.to_mongo())
        
    # B -> A
    series.qa_pair_collection_list = pair_collection_list
    return jsonify({'results': series, 'err_msg': err_msg}), HTTPStatus.OK

# 3.9 创建一个问答系列
@router_qa.route('/api/qa/series', methods=['POST'])
@jwt_required()
@use_args({"title": fields.Str(required=True), "doc_id_list": fields.List(fields.Str())}, location="json", unknown=UNKNOW)
def create_qa_series(data):
    user_id = get_jwt_identity()
    title = data.get("title")
    doc_id_list = data.get("doc_id_list", [])
    err_msg = dict()
    if title == "":
        err_msg['error'] = "问题框为空"
        return jsonify({'results': dict(), 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR

    # 创建系列id和集合id
    series_id = str(uuid.uuid4())
    collection_id = str(uuid.uuid4())
    # 获取创建时间
    now = datetime.now()
    time_string = now.strftime("%Y-%m-%d %H:%M:%S")

    # 在数据库中创建类对象
    try:
        qa_series = Qa_series(_id=series_id, user_id=user_id, title=title, create_time=time_string).save()
        qa_pair_collection = Qa_pair_collection(_id=collection_id, qa_series_id=series_id, create_time=time_string, order=0).save()
        qa_pair_collection_list = qa_series.qa_pair_collection_list
        qa_pair_collection_list.append(collection_id)
        qa_series.qa_pair_collection_list = qa_pair_collection_list
        qa_series.save()

        # 将指定的doc的series_id改为当前series的id，注意校验和用户是否对应
        doc_fail_list = []
        for doc_id in doc_id_list:
            docs = UploadDocument.objects(_id=doc_id)

            # 校验文件是否存在
            if docs is None:
                doc_fail_list.append([doc_id, "文件不存在！"])
                continue
            doc = docs.first()
            doc_user_id = doc.user_id

            # 校验文件是否属于当前用户
            if doc_user_id != user_id:
                doc_fail_list.append([doc_id, "文件不属于当前用户！"])
                continue
            doc.qa_series_id = series_id
            doc.selected = True
            doc.save()
        doc_msg = doc_fail_list if len(doc_fail_list) else ""

        # 返回结果
        results = dict({"qa_series_id": series_id, "qa_pair_collection_id": collection_id, "doc_msg": doc_msg})
        # results = dict({"qa_series_id": series_id, "qa_pair_collection_id": collection_id})
        
    except Exception as e:
        err_msg['error'] = str(e)
        return jsonify({'results': dict(), 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'results': results, 'err_msg': err_msg}), HTTPStatus.OK

# 3.10 创建一个问答集合
@router_qa.route('/api/qa/collection', methods=['POST'])
@jwt_required()
@use_args({"qa_series_id": fields.Str(required=True)}, location="json", unknown=UNKNOW)
def create_qa_collection(data):
    err_msg = dict()
    try:
        qa_series_id = data.get("qa_series_id")
        id = str(uuid.uuid4())
        now = datetime.now()
        time_string = now.strftime("%Y-%m-%d %H:%M:%S")
        qa_series = Qa_series.objects(_id=qa_series_id).first()
        if not qa_series:
            err_msg["error"] = "无此问答系列！"
            return jsonify({'results': "", 'err_msg': err_msg}), HTTPStatus.BAD_REQUEST
        qa_series = Qa_series.objects(_id=qa_series_id, is_qa_delete=False).first()
        qa_pair_collection_list = qa_series.qa_pair_collection_list
        order = len(qa_pair_collection_list)
        qa_pair_collection = Qa_pair_collection(_id=id, qa_series_id=qa_series_id, create_time=time_string, order=order).save()
        # 更新问答系列的问答对集合列表
         
        qa_pair_collection_list.append(id)
        qa_series.qa_pair_collection_list = qa_pair_collection_list
        qa_series.save()

        results = dict({"qa_series_id":qa_series_id,"qa_pair_collection_id":id})
    except Exception as e:
        err_msg["error"] = str(e)
        return jsonify({'results': dict(), 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'results': results, 'err_msg': err_msg}), HTTPStatus.OK

# 3.11 问题补充
@router_qa.route('/api/qa/complete/ask', methods=['POST'])
@use_args({"query": fields.Str(required=True),"qa_series_id": fields.Str(required=True),"qa_pair_collection_id": fields.Str(required=True),
           "type": fields.Str(required=True), "search_mode": fields.Str(required=True)}, location="json", unknown=UNKNOW)
@jwt_required()
def ask_complete(data):
    err_msg = dict()
    headers = {
    "Content-Type":"application/json"
    }
    user_id = get_jwt_identity()
    data['user_id'] = user_id

    pdf_objs = get_docs_with_series_id(data.get('qa_series_id'))
    pdf_ids = [item.obj_key for item in pdf_objs if item.selected]
    data['pdf_ids'] = pdf_ids

    if data.get('search_mode') in ["doc",'doc_pro']:
        headers["function"] = "doc_supply_question"
    else:
        headers["function"] = "supply_question"
    algorithm_endpoint = f"{algorithm_url}/execute"

    request_id = request.headers.get('X-Request-Id')
    headers["request-id"] = request_id
    session_id = data['qa_series_id']
    headers["session-id"] = session_id

    language = request.headers.get("language", "zh-CN")
    headers['language'] = language
    
    user_id = get_jwt_identity()
    data['user_id'] = user_id

    log_data={}
    log_data["Request_url"] = "supply_question"
    log_data["Request_headers"] = headers
    log_data["Request_data"] = data
    logger.info(log_data)

    qa_pair_id = str(uuid.uuid4())
    data['qa_pair_id'] = qa_pair_id
    """
    todo: 目前只有互联网检索有pro模式，其他均为非pro模式
    """
    # data['pro_flag'] = True if 'pro' in data.get('search_mode') else False
    search_mode = data.get('search_mode')
    if search_mode == 'pro':
        data['pro_flag'] = True
    else:
        data['pro_flag'] = False
    
    # 创建问答对
    qa_pair_collection = Qa_pair_collection.objects(_id=data['qa_pair_collection_id']).first()
    qa_pair_collection.update(query=data["query"])
    lversion = len(qa_pair_collection.qa_pair_list)
    now = datetime.now()
    time_string = now.strftime("%Y-%m-%d %H:%M:%S")
    Qa_pair(_id=qa_pair_id, version=lversion, qa_pair_collection_id=data['qa_pair_collection_id'], qa_series_id=data['qa_series_id'],
            query=data['query'], search_mode=data['search_mode'], create_time=time_string).save()
    pair_list = qa_pair_collection.qa_pair_list
    pair_list.append(qa_pair_id)
    qa_pair_collection.save()
    qa_pair = Qa_pair.objects(_id=qa_pair_id).first()
    try:
        response = requests.post(algorithm_endpoint, json=data, headers = headers)

        log_data={}
        log_data["Response_url"] = "supply_question"
        log_data["Response_data"] = response.json()
        logger.info(log_data)
        
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get('results')
            results['qa_pair_id'] = qa_pair_id
            if results['type'] == "additional_query":
                additional_query_data = results['additional_query']
                qa_pair_info=Qa_pair_info(additional_query = additional_query_data)
                qa_pair.update(qa_info=qa_pair_info)
                results['additional_query'] = qa_pair_info.additional_query
            qa_pair.update(unsupported = results["unsupported"])
            return jsonify({'results': results, 'err_msg': err_msg}), HTTPStatus.OK
        else:
            err_msg["error"] = f"Request failed with status code {response.status_code}"
            return {"err_msg": err_msg}, response.status_code
    except requests.RequestException as e:
        err_msg["error"] =  f"Request failed: {e}"
        return {"err_msg": err_msg}, HTTPStatus.INTERNAL_SERVER_ERROR

def format_return(content):
    res = {"results":content, "err_msg":""}
    return f"data: {json.dumps(res, ensure_ascii=False)}\n\n".encode()

def mock_doc_algo():
    analyze_notice = {
        "type": "state",
        "data": "analyze",
        "query": "query",
        "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
        "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
        "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
    }
    yield format_return(analyze_notice)
    search_notice = {
        "type": "state",
        "data": "search",
        "query": "query",
        "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
        "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
        "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
    }
    yield format_return(search_notice)
    organize_notice = {
        "type": "state",
        "data": "organize",
        "query": "query",
        "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
        "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
        "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
    }
    yield format_return(organize_notice)
    # qa_pair_info
    qa_pair_info = {
        "type": "qa_pair_info",
        "data": {
            "doc_num":10,
            "page_num":200,
            "word_num":3000,
            "search_query":"mock",
            "ref_docs":{
                "test_doc_id":{
                    "_id":"test_doc_id",
                    "doc_name":"中国银行业数字化转型研究报告.pdf",
                }
            },
        },
        "query": "query",
        "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
        "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
        "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
    }
    yield format_return(qa_pair_info)
    # ref_answer
    
    ref_answer = {
        "type": "ref_answer", 
        "data": [
                {
                    "_id": "[VEgvTNgR]", 
                    "news_id": "test_doc_id", 
                    "content": "落地支撑指南：报告将基于不同银行营销场景下数字化最佳实践，结合调研结果，从不同的角度分析如何构建银行营销数字化转型支撑体系，助力银行营销数字化转型的落地。"}
            ]
    }
    yield format_return(ref_answer)
    # complete
    complete_notice = {"type": "state", "data": "complete", "query": "特朗普遭受枪击", 
                        "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
                        "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
                        "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"}
    yield format_return(complete_notice)
    # text
    text = {"type": "text", "data": "落地支撑指南[VEgvTNgR]", "query": "特朗普遭受枪击", 
            "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
            "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
            "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
            }
    yield format_return(text)
    text_end = {"type": "text_end", "data": "", "query": "特朗普遭受枪击", 
                "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
                "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
                "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
                }
    yield format_return(text_end)
    # recommendation
    recommendation_notice = {"type": "recommendation", "data": ["特朗普遭受枪击事件对2024年美国大选产生了哪些影响？", "特朗普在遭受枪击后，他的支持率是否有所变化？", "枪击事件后，特朗普的安保措施是否得到了加强？"], "query": "特朗普遭受枪击", 
                            "qa_series_id":"db5cf9d1-0feb-4e79-b1e7-b9e1da41913a",
                            "qa_pair_collection_id": "285d89f5-26dd-4cd5-9ffb-2ac532ad9198",
                            "qa_pair_id": "5ddaae84-24b2-4a82-8bef-3c86916957d8"
                             }
    yield format_return(recommendation_notice)
    # done
    yield 'data: [DONE]\n\n'

class AdditionalQuerySchema(Schema):
    options = fields.List(fields.String(), default=[])
    selected_option = fields.List(fields.String(), default=[])
    other_option = fields.String()
    title = fields.String()

import pandas as pd
import tldextract
df = pd.read_csv('controllers/icon4.csv')
oss_url = "https://xxx.oss-cn-shanghai.aliyuncs.com/"
host_to_oss_id = pd.Series(df.oss_id.values, index=df.host).to_dict()
host1_to_oss_id = pd.Series(df.oss_id.values, index=df.host_1).to_dict()
# 3.12 问题回答
# 同一个qa_c要记得更新qa_c对pair的list + ip
@router_qa.route('/api/qa/ask', methods=['POST'])
@jwt_required()
@use_args({"query": fields.Str(required=True),"qa_series_id": fields.Str(required=True),"qa_pair_collection_id": fields.Str(required=True),
           "qa_pair_id": fields.Str(),"delete_news_list": fields.List(fields.Str()),"type": fields.Str(required=True),
           "additional_query": fields.Nested(AdditionalQuerySchema()), "search_mode":fields.Str(required=True)
           }, location="json", unknown=UNKNOW)
def ask_question(data):
    err_msg = dict()
    client_ip = request.remote_addr
    data["ip"] = client_ip
    qa_c = Qa_pair_collection.objects(_id=data.get("qa_pair_collection_id")).first()
    search_mode = data.get("search_mode", "")
    user_id = get_jwt_identity()
    data['user_id'] = user_id

    # mock 文档检索，待改
    if search_mode in ['doc','doc_pro']:
        ainewsqa_func = 'doc_answer'
    else:
        ainewsqa_func = 'answer'

    pdf_objs = get_docs_with_series_id(data.get('qa_series_id'))
    pdf_ids = [item.obj_key for item in pdf_objs if item.selected]
    data['pdf_ids'] = pdf_ids

    if search_mode not in SEARCH_MODES: # 校验检索模式
        err_msg["error"] = "检索模式不正确/不存在！"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND

    if not qa_c:
        err_msg["error"] = "该问答对集合不存在！"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    
    # 校验qa_series_id和qa_pair_collection_id是否正确对应
    if qa_c.qa_series_id != data.get("qa_series_id"):
        err_msg["error"] = "问答序列对应错误！"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    
    qa_pair_id =data.get("qa_pair_id")
    qa_pair_mongo = Qa_pair.objects(_id=qa_pair_id).first()
    if not qa_pair_mongo:
        err_msg["error"] = "该问答对不存在！"
        return jsonify({'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    # 修改qa_pair的检索模式
    qa_pair_mongo.search_mode = search_mode
    qa_pair_mongo.save()

    def saveQaPair(qa_pair, qa_pair_mongo):
        qa_info_tosave = qa_pair['qa_info']
        qa_info_tosave.pop("sites")

        qa_pair_info_mongo = Qa_pair_info(site_num=qa_info_tosave['site_num'],
                     page_num=qa_info_tosave['page_num'],
                     word_num=qa_info_tosave['word_num'],
                     additional_query=qa_info_tosave['additional_query'],
                     search_query=qa_info_tosave['search_query'],
                     ref_pages=qa_info_tosave['ref_pages'],
                     )

        qa_pair_mongo.qa_info = qa_pair_info_mongo
        qa_pair_mongo.general_answer = qa_pair['general_answer']
        qa_pair_mongo.recommend_query = qa_pair['recommend_query']
        qa_pair_mongo.reference = qa_pair['reference']
        qa_pair_mongo.images = qa_pair['images']
        # 创建timeline类
        if qa_pair.get('timeline'):
            _id = str(uuid.uuid4())
            now = datetime.now()
            time_string = now.strftime("%Y-%m-%d %H:%M:%S")
            Timeline(_id=_id, data=qa_pair['timeline'], create_time=time_string).save()
            qa_pair_mongo.timeline_id = _id
        qa_pair_mongo.save()

    # 算法接口url
    url = algorithm_url + "/stream_execute"
    headers = {
        "Content-Type":"application/json"
    }
    language = request.headers.get("language", "zh-CN")
    headers['language'] = language
    
    headers["function"] = ainewsqa_func
    request_id = request.headers.get('X-Request-Id')
    headers["request-id"] = request_id
    session_id = data['qa_series_id']
    headers["session-id"] = session_id

    # 创建线程安全队列用于返回处理结果
    data_queue = queue.Queue()

    # 提取 `process_data` 为一个独立线程
    def process_data(response):
    # 处理流式数据函数

        def format_return(content):
            res = {"results":content, "err_msg":""}
            return f"data: {json.dumps(res, ensure_ascii=False)}\n\n".encode()
        
        def format_ref_page(recall_data_ref_pages):
            new_format = {
                "_id":"",
                "url":"",
                "site":"",
                "title":"",
                "summary":"",
                "content":"",
                "icon":""
            }
            siteList = set()
            return_recall_data = {}
            for key in recall_data_ref_pages.keys():
                new_format = {}
                doc_id = recall_data_ref_pages[key]['_id']
                if 'doc' in search_mode:
                    try:
                        doc_name = UploadDocument.objects(doc_id=doc_id).first().name
                        file_type = UploadDocument.objects(doc_id=doc_id).first().format
                        # new_format['title'] = UploadDocument.objects(doc_id=doc_id).first().name
                    except:
                        doc_name = UploadDocument.objects(name=doc_id).first().name
                        file_type = UploadDocument.objects(name=doc_id).first().format
                        # new_format['title'] = UploadDocument.objects(name=doc_id).first().name
                    new_format['title'] = f"{doc_name}.{file_type}"
                else:
                    new_format['title'] = recall_data_ref_pages[key]['title']
                new_format['_id'] = doc_id
                new_format['url'] = recall_data_ref_pages[key]['url']
                ext = tldextract.extract(new_format['url'])
                new_format['site'] = ext.fqdn
                siteList.add(new_format['site'])

                new_format['summary'] = recall_data_ref_pages[key]['summary']
                new_format['content'] = recall_data_ref_pages[key]['content']
                new_format['icon'] = recall_data_ref_pages[key]['icon']
                icon_url = host_to_oss_id.get(new_format['site'])
                if not icon_url:
                    icon_url = host1_to_oss_id.get(new_format['site'])
                    if icon_url:
                        icon_url = oss_url + icon_url
                        new_format['icon'] = icon_url
                else:
                    icon_url = oss_url + icon_url
                    new_format['icon'] = icon_url

                return_recall_data[key] = new_format

            return return_recall_data, list(siteList)

        def renew_qa_info(qa_info, ref_pages):
            format_ref_pages, siteList = format_ref_page(ref_pages)
            ref_pages = format_ref_pages
            ## 去重page
            qa_info['ref_pages'].update(ref_pages)
            qa_info['page_num'] = len(qa_info['ref_pages'])

            word_num = 0
            ref_pages = qa_info['ref_pages']
            for key in ref_pages.keys():
                word_num += len(ref_pages[key]['content'])
            qa_info['word_num'] = word_num

            before_site_list = copy.deepcopy(qa_info['sites'])
            before_site_list += siteList
            qa_info['sites'] = list(set(before_site_list))
            qa_info['site_num'] = len(qa_info['sites'])

            return qa_info

        def format_qa_pair_info(qa_info):
            format = {
                "type":"qa_pair_info",
                "data":qa_info,
                "query":data.get("query"),
                "qa_series_id":data.get("qa_series_id"),
                "qa_pair_collection_id":data.get("qa_pair_collection_id"),
                "qa_pair_id":qa_pair_id
            }
            return format

        # 提示前端，分析开始
        analyze_notice = {
            "type": "state",
            "data": "analyze",
            "query": data.get("query"),
            "qa_series_id": data.get("qa_series_id"),
            "qa_pair_collection_id": data.get("qa_pair_collection_id"),
            "qa_pair_id": qa_pair_id
        } 
        data_queue.put(format_return(analyze_notice))
        # yield format_return(analyze_notice)

        qa_pair = {
            "_id":data.get('qa_pair_id'),
            'qa_info':{},
            'general_answer':"",
            'timeline_id':"",
            'timeline':"",
            'recommend_query':"",
            'reference':"",
            'images':[]
        }
        qa_info = {
            "site_num":0,
            "sites":[],
            "page_num":0,
            "word_num":0,
            "additional_query":{},
            "search_query":[],
            "ref_pages":{},
        }
        # 从前端获取补充信息
        qa_info['additional_query'] = data.get("additional_query")

        text = ''
        # 获取算法侧返回的结果
        qa_pair["reference"] = []
        for chunk in response.iter_lines(chunk_size=1024, decode_unicode=False, delimiter=b"\0"):
            if chunk:
                content = chunk.decode('utf-8')
                if content.startswith("data: ") and content != "data: [DONE]\n\n":
                    content = content[len("data: "):]
                    content = json.loads(content.strip())

                    if content['type'] == "error":
                        data_queue.put(format_return(content))
                        return

                    if content['type'] == "state":
                        data_queue.put(format_return(content))
                        continue

                    if content['type'] == "intention_query":
                        qa_info['search_query'] = content['data']
                        continue

                    if content['type'] == "ref_page":
                        qa_info = renew_qa_info(qa_info, content['data'])
                        format_qa_info = format_qa_pair_info(qa_info)
                        data_queue.put(format_return(format_qa_info))
                        continue

                    if content['type'] == "ref_answer":
                        qa_pair["reference"] = content['data']
                        data_queue.put(format_return(content))
                        continue

                    if content['type'] == "text":
                        text += content['data']
                        data_queue.put(format_return(content))
                        continue

                    if content['type'] == "image":
                        qa_pair["images"] = content['data']
                        data_queue.put(format_return(content))
                        continue

                    if content['type'] == "recommendation":
                        qa_pair['recommend_query'] = content['data']
                        data_queue.put(format_return(content))
                        continue

                    if content['type'] == "timeline":
                        qa_pair['timeline'] = content['data']
                        data_queue.put(format_return(content))
                        continue

                    data_queue.put(format_return(content))
        data_queue.put('data: [DONE]\n\n')
        

        # 最终的持久化
        log_data={}
        log_data["Response_url"] = "answer_question"
        log_data["Response_data"] = text
        log_data["Response_timeline"] = qa_pair['timeline']
        log_data["Response_recommend_query"] = qa_pair['recommend_query']
        # log_data["Response_reference"] = qa_pair["reference"]
        # log_data["Response_qa_info"] = qa_info
        log_data["request_id"] = request_id
        log_data["session_id"] = session_id
        # logger.info(log_data)

        qa_pair['general_answer'] = text
        qa_pair["qa_info"] = qa_info
        saveQaPair(qa_pair, qa_pair_mongo)
        response_log.logger.info(log_data)

    def thread_func():
        try:
            response = requests.request("POST", url, headers=headers, json=data, stream=True)
            if response.status_code != HTTPStatus.OK:
                return Response("算法接口响应失败！", status=HTTPStatus.INTERNAL_SERVER_ERROR)
            if type(response) is not requests.models.Response:
                return Response("算法接口返回格式错误！", status=HTTPStatus.INTERNAL_SERVER_ERROR)

            # 等待算法结束后继续数据存储
            process_data(response)

        except Exception as e:
            return Response(f"回答问题接口异常：{e}", status=HTTPStatus.INTERNAL_SERVER_ERROR)



    log_data={}
    log_data["Request_url"] = "answer_question"
    log_data["Request_headers"] = headers
    log_data["Request_data"] = data
    logger.info(log_data)


    # 通过线程运行
    threading.Thread(target=thread_func, daemon=True).start()

    def consume_queue(data_queue):
        while True:
            content = data_queue.get()
            if content == 'data: [DONE]\n\n':
                break
            yield content

    stream_headers = {"Content-Type": "text/event-stream;charset=utf-8"}
    return Response(stream_with_context(consume_queue(data_queue)), headers=stream_headers, status=HTTPStatus.OK)
    # try:
    #     response = requests.request("POST", url, headers=headers, json=data, stream=True) 
    #     # 处理请求失败
    #     if response.status_code != HTTPStatus.OK:
    #         return Response("算法接口响应失败！", status=HTTPStatus.INTERNAL_SERVER_ERROR)
    #     # 校验返回格式
    #     if type(response) is not requests.models.Response:
    #         return Response("算法接口返回格式错误！", status=HTTPStatus.INTERNAL_SERVER_ERROR)
    #     # 继续以流式形式传给客户端
    #     stream_headers = {"Content-Type": "text/event-stream;charset=utf-8"}
    #     # resp = Response(stream_with_context(process_data(response)), headers=stream_headers, status=HTTPStatus.OK)
        
    #     threading.Thread(target=thread_func, daemon=True).start()
    
    # except Exception as e:
    #     # 若因为异常中断，保存当前的结果
    #     # qa_pair.save()
    #     return Response(f"回答问题接口异常：{e}", status=HTTPStatus.INTERNAL_SERVER_ERROR)
    # # 更新结果到数据库
    # ## 包括问答对存到问答集合的问答对list中
    # return resp


# 3.13 查看单个问答对
@router_qa.route('/api/qa/pair/<qa_pair_id>', methods=['GET'])
@jwt_required()
def get_single_pair(qa_pair_id):
    err_msg = dict()
    try:
        # 查询符合条件的问答对
        qa_pair = Qa_pair.objects(_id=qa_pair_id).first()
        results = qa_pair
        t_id = qa_pair.timeline_id
        # E
        t = Timeline.objects(_id=t_id).first()
        if t:
        # E -> C
            timeline = t.data
            qa_pair.timeline_id = timeline
        # C -> B
    except Exception as e:
        err_msg["error"] = str(e)
        return jsonify({'results': dict(), 'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'results': results, 'err_msg': err_msg}), HTTPStatus.OK

# 3.14 结果页转新闻稿  --> 总论点生成接口

# 3.15 订阅功能
@router_qa.route('/api/qa/subscribe', methods=['POST'])
@jwt_required()
@use_args({"qa_series_id": fields.Str(required=True),"qa_pair_collection_id": fields.Str(required=True),
           "query": fields.Str(required=True),"push_interval": fields.Int(required=True),"push_time": fields.Str(required=True),
           "end_time": fields.Str(required=True),"email": fields.Str(required=True),
           }, location="json", unknown=UNKNOW)
def create_subscribe(data):
    err_msg = dict()
    user_id = get_jwt_identity()
    # 订阅信息存入数据库
    id = str(uuid.uuid4())
    now = datetime.now()
    time_string = now.strftime("%Y-%m-%d %H:%M:%S")
    date_string = now.strftime("%Y-%m-%d")
    qa_series = Qa_series.objects(_id=data["qa_series_id"], is_qa_delete=False).first()
    qa_c = Qa_pair_collection.objects(_id=data["qa_pair_collection_id"]).first()
    # 存在检验
    if not qa_series or not qa_c:
        err_msg["error"] = "无此问答系列或无此问答集合！"
        return jsonify({'status': False, 'err_msg': err_msg}), HTTPStatus.BAD_REQUEST
    try:
        subscription = Subscription(_id=id, qa_series_id=data["qa_series_id"], qa_pair_collection_id=data["qa_pair_collection_id"],
                                query=data["query"], push_interval=data["push_interval"], push_time=data["push_time"], 
                                end_time=data["end_time"], email=data["email"], user_id=user_id,
                                fresh_time = date_string, create_time=time_string).save()
        qa_c.update(is_subscribed = True,subscription_id = id)
        status = True
    except Exception as e:
        err_msg["error"] = str(e)
        status = False
    return jsonify({'status': status, 'err_msg': err_msg}), HTTPStatus.OK

# 3.16 取消订阅
@router_qa.route('/api/qa/subscribe', methods=['DELETE'])
@jwt_required()
@use_args({"qa_pair_collection_id": fields.Str(required=True)}, location="json", unknown=UNKNOW)
def delete_subscribe(data):
    err_msg = dict()
    qa_c = Qa_pair_collection.objects(_id=data["qa_pair_collection_id"]).first()
    subscription_id = qa_c.subscription_id
    subscription = Subscription.objects(_id=subscription_id).first()
    if not subscription:
        err_msg["error"] = "无此订阅记录！"
        return jsonify({'status': False,'err_msg': err_msg}), HTTPStatus.NOT_FOUND
    try:   
        subscription.delete()
        qa_c.update(is_subscribed = False,subscription_id = "")
        return jsonify({'status': True, 'message': '订阅记录已成功删除！'}), HTTPStatus.OK
    except Exception as e:
        err_msg["error"] = f"删除订阅记录时发生错误：{str(e)}"
        return jsonify({'status': False,'err_msg': err_msg}), HTTPStatus.INTERNAL_SERVER_ERROR

# 创建qa_pair
@router_qa.route('/api/qa/pair/create', methods=['POST'])
@use_args({"query": fields.Str(required=True),"qa_series_id": fields.Str(required=True),"qa_pair_collection_id": fields.Str(required=True),
           "search_mode": fields.Str(required=True)
           }, location="json", unknown=UNKNOW)
@jwt_required()
def create_qa_pair(data):
    try:
        qa_pair_id = str(uuid.uuid4())
        qa_pair_collection = Qa_pair_collection.objects(_id=data['qa_pair_collection_id']).first()
        qa_pair_collection.update(query=data["query"])
        lversion = len(qa_pair_collection.qa_pair_list)
        now = datetime.now()
        time_string = now.strftime("%Y-%m-%d %H:%M:%S")
        Qa_pair(_id=qa_pair_id, version=lversion, qa_pair_collection_id=data['qa_pair_collection_id'], qa_series_id=data['qa_series_id'],
                query=data['query'], create_time=time_string).save()
        pair_list = qa_pair_collection.qa_pair_list
        pair_list.append(qa_pair_id)
        qa_pair_collection.save()
        qa_pair = Qa_pair.objects(_id=qa_pair_id).first()

        # 设置search_mode
        qa_pair.search_mode = data.get('search_mode', "pro")
        qa_pair.save()
        results = dict({"qa_pair_id": qa_pair_id})
    except Exception as e:
            return jsonify({'results': dict(), 'err_msg': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'results': results, 'err_msg': ""}), HTTPStatus.OK

def get_doc_info_from_mongo(doc_id):
    doc_info = UploadDocument.objects(doc_id=doc_id).first()
    return doc_info

def get_doc_info_by_id(_id):
    doc_info = UploadDocument.objects(_id=_id).first()
    return doc_info

# 文件预览
@router_qa.route('/api/doc_search/<doc_id>', methods=['GET'])
@jwt_required()
def preview_doc(doc_id):
    doc_info = get_doc_info_from_mongo(doc_id)
    doc_name = doc_info['name']
    doc_ext = doc_info['format']
    doc_full_name = f"{doc_name}.{doc_ext}"

    doc_obj_key = doc_info['obj_key']
    prefix_to_remove = "oss://"
    doc_obj_key = doc_obj_key.replace(prefix_to_remove, "")
    if doc_ext == 'doc':
        doc_obj_key = doc_obj_key.replace("doc", "pdf")
    if doc_ext == 'docx':
        doc_obj_key = doc_obj_key.replace("docx", "pdf")

    doc_obj = read_material_from_oss_v2(doc_obj_key)

    response = make_response(
            send_file(doc_obj, download_name=doc_full_name, as_attachment=True))
    return response, HTTPStatus.OK

def get_docs_with_series_id(qa_series_id):
    doc_infos = UploadDocument.objects(qa_series_id=qa_series_id)
    return doc_infos

def filter_doc_infos(doc_infos):
    keys_to_extract = ["doc_id", "user_id", "qa_series_id", "size", "name", "format", "selected"]
    filtered_docs = list()
    for doc_info in doc_infos:
        doc_res = dict()
        for key in keys_to_extract:
            if key == 'doc_id':
                doc_res['_id'] = doc_info[key]
            else:
                doc_res[key] = doc_info[key]

        # 把时间转为timestamp
        timestamp = int(datetime.strptime(doc_info['create_time'], "%Y-%m-%d %H:%M:%S").timestamp())
        doc_res['date'] = timestamp

        filtered_docs.append(doc_res)

    return filtered_docs

# 文件列表查询
@router_qa.route('/api/doc_search/doc_list/<qa_series_id>', methods=['GET'])
@jwt_required()
def list_doc(qa_series_id):
    doc_infos = get_docs_with_series_id(qa_series_id)
    filtered_docs = filter_doc_infos(doc_infos)
    res = {
        "doc_list": filtered_docs,
        "msg": qa_series_id,
    }
    return jsonify(res), HTTPStatus.OK

# 文件删除,oss层不做操作，只做doc_id和qa_series_id的解绑
@router_qa.route('/api/doc_search/doc', methods=['DELETE'])
@use_args({"doc_id": fields.Str(required=True),"qa_series_id": fields.Str(required=True)
           }, location="json", unknown=UNKNOW)
@jwt_required()
def delete_doc(data):
    # 获取请求参数
    doc_id = data['doc_id']
    qa_series_id = data['qa_series_id']

    ## 校验文件是否 存在 且 属于问答系列
    doc_info = get_doc_info_by_id(doc_id)
    if not doc_info:
        return {"err":"文件不存在！"}, HTTPStatus.BAD_REQUEST

    if doc_info['qa_series_id'] != qa_series_id:
        return {"err":"文件不属于当前问答系列！"}, HTTPStatus.BAD_REQUEST
    
    try:
        res = doc_info.update(qa_series_id="")
    except Exception as e:
        return jsonify({'err': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    res = {
        "doc_id": doc_id,
        "msg": "文件绑定状态问答状态已删除！",
    }
    # # 在mongo中删除文件信息
    # doc_obj_key = doc_info['obj_key']
    # doc_info.delete()
    # # 在minio中删除文件对象
    # res_msg = delete_material_from_oss(doc_obj_key, "doc_search")
    return jsonify(res), HTTPStatus.OK

# 更新文件选中状态
@router_qa.route('/api/doc_search/update_select', methods=['PUT'])
@use_args({"doc_id": fields.Str(required=True),"selected": fields.Bool(required=True)
           }, location="json", unknown=UNKNOW)
@jwt_required()
def update_select(data):
    doc_id = data.get("doc_id", "")
    qa_series_id = data.get("qa_series_id", "")
    selected = data.get("selected", None)
    doc_info = UploadDocument.objects(qa_series_id=qa_series_id).filter(doc_id=doc_id).first()
    if not doc_info:
        return jsonify({'err': "文件不存在，无法更新文件选中状态！"}), HTTPStatus.BAD_REQUEST
    # 更新选中状态
    try:
        res = doc_info.update(selected=selected)
    except Exception as e:
        return jsonify({'err': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

    res = {
        "doc_id": doc_id,
        "selected": selected,
        "msg": "文件选中状态更新成功！",
    }
    return jsonify(res), HTTPStatus.OK