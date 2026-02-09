from http import HTTPStatus

from controllers import UNKNOW
from flask import Blueprint, jsonify, current_app, request
from config import llm_log, config_manager
from flask_jwt_extended import jwt_required, get_jwt_identity
from webargs import fields
from webargs.flaskparser import use_args
import time
import requests
import traceback
import json

from material import search_file_info_by_material_ids_from_es

URL_ALGORITHM = config_manager.alg_tmp_url 
URL_ALGORITHM_SUB_TITLE = f"{URL_ALGORITHM}/api/chat/doc/generate_sub_title"
URL_ALGORITHM_REVIEW = f"{URL_ALGORITHM}/api/chat/doc/generate_review"
URL_ALGORITHM_STRUCTURE = f"{URL_ALGORITHM}/api/chat/doc/structure"


router_ai_material = Blueprint('ai_material', __name__)

# mongo_client = pymongo.MongoClient(host=mongo_config['Host'], port=int(mongo_config['Port']), 
#                                    username=mongo_config['Username'], password=mongo_config['Password'], authSource=mongo_config['authDB'])
# mong_db = mongo_client.llm
# collection = mong_db['context']

@router_ai_material.route('/api/ai/material/generate_sub_title', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True),"session_id": fields.Str(required=True),
            "topic": fields.Str(),
            "material_id": fields.List(cls_or_instance=fields.Str(),required=True),
            "sub_title_his": fields.List(cls_or_instance=fields.Dict(),requried=True),
            "require": fields.Str(required=False),"kind": fields.Str(required=True), "review_length": fields.Int(requried=False),
            "style": fields.Str(required=True), "direction": fields.Str(required=False),
            }, location="json", unknown=UNKNOW)
def generate_sub_title(data):
    """
    根据用户上传的素材进行小标题生成
    :require: 用户选择重新生成的要求

    Returns: 返回生成的小标题
    """    
    try:
        language = request.headers.get("language", "zh-CN")

        request_id = data['request_id']
        session_id = data['session_id']
        topic = data.get('topic', "")
        material_id= data.get('material_id', [])
        sub_title_his = data.get('sub_title_his',[])
        review_length = data.get('review_length', -1)
        material_flag = do_generate_material_flag(material_id)
        user_id = get_jwt_identity()
        # structure = do_generate_structure(request_id,
        #                                   session_id,
        #                                   material_id,
        #                                   material_flag)

        # if structure == None:
        #     return jsonify({'message': f"文档结构化时出现错误"}), HTTPStatus.INTERNAL_SERVER_ERROR

        structure = None
        
        direction = data.get('direction','')
        sub_titles = do_generate_sub_title(request_id, 
                                           session_id, 
                                           material_id, 
                                           sub_title_his, 
                                           material_flag,
                                           topic,
                                           structure,
                                           data['kind'],
                                           data['style'],
                                           direction, review_length, user_id, language)
        if sub_titles == None:
            return jsonify({'message': f"提炼要点时出现错误"}), HTTPStatus.INTERNAL_SERVER_ERROR

        return jsonify({'result': sub_titles, 'message': ''}), HTTPStatus.OK
    

    except Exception as e:        
        current_app.logger.error(f"error when generating sub_title, {e}, {traceback.format_exc()}")
        return jsonify({'message': f"server error, {e}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@router_ai_material.route('/api/ai/material/generate_review', methods=['POST'])
@jwt_required()
@use_args({"request_id": fields.Str(required=True),
           "session_id": fields.Str(required=True),
           "topic": fields.Str(),
           "material_id": fields.List(cls_or_instance=fields.Str(),required=True), 
           "sub_title": fields.List(cls_or_instance=fields.Dict(),requried=True),            
           "result_his": fields.List(cls_or_instance=fields.Dict(),requried=True), 
           "review_length": fields.Int(requried=False),
           "use_trusted_website": fields.Bool(requried=False),"kind": fields.Str(required=True),
           "style": fields.Str(required=True), "direction": fields.Str(required=False),
          }, location="json", unknown=UNKNOW)
def generate_review(data):
    """
    全文生成

    Returns: 返回生成的全文
    """ 

    language = request.headers.get("language", "zh-CN")
    
    request_id = data['request_id']
    session_id = data['session_id']
    topic = data.get('topic', "")
    material_id= data.get('material_id', [])
    sub_title = data.get('sub_title',[])
    result_his = data.get('result_his',[])
    use_trusted_website = data.get('use_trusted_website',False)
    review_length = data.get('review_length', -1)
    user_id = get_jwt_identity()



    material_flag = do_generate_material_flag(material_id)
    # structure = do_generate_structure(request_id,
    #                                     session_id,
    #                                     material_id,
    #                                     material_flag)

    # if structure == None:
    #     return jsonify({'message': f"文档结构化时出现错误"}), HTTPStatus.INTERNAL_SERVER_ERROR

    structure = None
    direction = data.get('direction','')
    review = do_generate_review(request_id,
                                session_id,
                                material_id,
                                sub_title,
                                material_flag,
                                topic,
                                structure,
                                result_his,
                                use_trusted_website,
                                data['kind'],
                                data['style'],
                                direction, review_length, user_id, language)
    if review == None:
        return jsonify({'message': f"生成全文时出现错误"}), HTTPStatus.INTERNAL_SERVER_ERROR
    

    materials = search_file_info_by_material_ids_from_es(material_id)
    res = {
        "materials": materials,
        "review": review
    }
    return jsonify({'result': res, 'message': ''}), HTTPStatus.OK


def do_generate_material_flag(material_id):
    material_flag = {}
    for mid in material_id:
        material_flag[mid] = 0 
    return material_flag
    
# def do_generate_structure(request_id, session_id, material_id, material_flag): 
#     d = {
#         "request_id": request_id,
#         "session_id": session_id,
#         "material_id": material_id,
#         "material_flag": material_flag
#     }
#     res = requests.post(url=URL_ALGORITHM_STRUCTURE, json=d)
#     if res.ok:
#          res_data = json.loads(res.text)
#          if res_data['is_success']:
#              return res_data['result']
#     current_app.logger.error(f"error when generating structure: {d} , {res.text}")
#     return None


def do_generate_sub_title(request_id,
                          session_id,
                          material_id,
                          sub_title_his,
                          material_flag,
                          topic,
                          doc_strcture, 
                          kind,style,direction, review_length, user_id, language):
    headers = {"language": language}
    
    d = {
        "request_id": request_id,
        "session_id": session_id,
        "material_id": material_id,  
        "sub_title_his": sub_title_his,
        "doc_strcture": doc_strcture,
        "topic": topic,
        "material_flag": material_flag,
        "kind": kind,
        "style": style,
        "direction": direction,"review_length": review_length,
        "user_id": user_id
    }
    res = requests.post(url=URL_ALGORITHM_SUB_TITLE,headers=headers,json=d)
    if res.ok:
         res_data = json.loads(res.text)
         if res_data['is_success']:
             return res_data['result']
    current_app.logger.error(f"error when generating sub title: {d}, {res.text}")
    return None


def do_generate_review(request_id,
                       session_id,
                       material_id,
                       sub_title,
                       material_flag,
                       topic,
                       doc_strcture,
                       result_his,
                       use_trusted_website,
                       kind,style,direction, review_length, user_id, language):
    
    headers = {"language": language}
    search_field={
        "user_field":{
            "group_ids":[], 
            "material_ids": material_id,
        }
    }
    if use_trusted_website:
        search_field['net_field']={
            'is_filter':True
        }


    d = {
        "request_id": request_id,
        "session_id": session_id,
        "material_id": material_id,  
        "search_field": search_field,
        "sub_title": sub_title,
        "doc_strcture": doc_strcture,
        "topic": topic,
        "material_flag": material_flag,
        "result_his": result_his,
        "kind": kind,
        "style": style,
        "direction": direction,
        "review_length": review_length,
        "extend": {"credible": False},
        "user_id": user_id
    }
    if use_trusted_website:
        d['extend']['credible'] = use_trusted_website


    res = requests.post(url=URL_ALGORITHM_REVIEW,headers=headers,json=d)
    if res.ok:
         res_data = json.loads(res.text)
         if res_data['is_success']:
             return res_data['result']
    current_app.logger.error(f"error when generating sub title: {d}, {res.text}")
    return None

