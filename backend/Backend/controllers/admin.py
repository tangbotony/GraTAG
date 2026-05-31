import copy
import json
from http import HTTPStatus
from mongoengine.queryset.visitor import Q
from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from models.document import FILE_TYPE_DOCUMENT, Document
from models.user import User
from webargs import fields
from webargs.flaskparser import use_args
import os, sys
import uuid
from auth import access_type_check

router_admin = Blueprint('admin', __name__)

admin_user = "admin"

# admin 分享文档
@router_admin.route('/api/share/document', methods=['POST'])
@jwt_required()
@access_type_check
@use_args({"doc_id": fields.Str(required=True)}, location="json")
def share_document(data):
    user_id = get_jwt_identity()
    doc_id = data.get('doc_id')

    doc = Document.objects(_id=doc_id, user_id=user_id, is_trash=False, is_delete=False).first()
    if not doc:
        return jsonify({'message': "未在您的文件库中找到该文件 或 您无该篇文档的操作权限"}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    user_list = User.objects().all()
    for user in user_list:
        if user._id == user_id:
            continue
        d = Document(_id=doc._id + "_" + user._id, user_id=user._id, name=doc.name, text=doc.text, plain_text=doc.plain_text, parent_id=doc.parent_id, type=FILE_TYPE_DOCUMENT,
                    path=doc.path, create_time=doc.create_time, update_time=doc.update_time, extend_data={}, editable=False, shared=True).save()
        del d
    return jsonify({'message': "", 'status': 1}), HTTPStatus.OK

# admin 删除分享文档
@router_admin.route('/api/delete/document', methods=['POST'])
@jwt_required()
@access_type_check
@use_args({"doc_id": fields.Str(required=True)}, location="json")
def delete_share_document(data):
    user_id = get_jwt_identity()
    doc_id = data.get('doc_id')

    doc = Document.objects(_id=doc_id, user_id=user_id, is_trash=False, is_delete=False).first()
    if not doc:
        return jsonify({'message': "未在您的文件库中找到该文件 或 您无该篇文档的操作权限"}), HTTPStatus.INTERNAL_SERVER_ERROR

    user_list = User.objects().all()
    for user in user_list:
        docs = Document.objects(user_id=user._id, is_trash=False, is_delete=False, editable=False, shared=True).all()
        if docs is None:
            continue
        for d in docs:
            if doc._id in d._id:
                d.delete()
    # doc.delete()    
    return jsonify({'message': "", 'status': 1}), HTTPStatus.OK

# admin 添加底纹
@router_admin.route('/api/admin/add_shading', methods=['POST'])
@jwt_required()
@access_type_check
@use_args({"event": fields.Str(required=True), "argument": fields.Str(required=True), "evidence": fields.Str(required=True)}, location="json")
def add_shading(data):
    user_id = get_jwt_identity()
    path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    final_path = os.path.join(path, 'config/Shading.json') 
    with open(final_path, 'w', encoding="utf-8") as file:
        file.write(json.dumps({"event": data.get('event'), 'argument': data.get('argument'), "evidence": data.get('evidence')})) 
    return jsonify({'message': "", 'status': 1}), HTTPStatus.OK

def permitted(sub_user_type, super_user_type):
    if sub_user_type == 'normal' and super_user_type == 'admin' \
    or sub_user_type == 'normal' and super_user_type == 'super_admin' \
    or sub_user_type == 'admin' and super_user_type == 'super_admin':
        return True
    else:
        return False

# admin 添加用户
@router_admin.route('/api/admin/add_user', methods=['POST'])
@jwt_required()
@access_type_check
@use_args({"name": fields.Str(required=True), "passwd": fields.Str(required=True), 
           "max_devices": fields.Int(required=True), "create_date": fields.Str(required=True), 
           "expire_date": fields.Str(required=True), "department": fields.Str(required=True), 
           "real_name": fields.Str(), "phone": fields.Str(), 
           "access_type": fields.Str(default="normal"), 
           "email": fields.Str(),
           "remark": fields.Str(),
           },
           location="json")
def add_user(data):
    user_id = get_jwt_identity()
    id = str(uuid.uuid4())
    super_user = User.objects(_id=user_id).first()
    user_name = data.get('name')
    if not user_name:
        return jsonify({'message': "用户名不能为空"}), HTTPStatus.BAD_REQUEST
    db_user = User.objects(name=user_name).first()
    if db_user:
        return jsonify({'message': "用户名已存在, 不能重复"}), HTTPStatus.BAD_REQUEST
    # 校验子账户的账户等级是否超过了当前账号
    sub_user_type = data.get('access_type')
    super_user_type = super_user.access_type
    if not permitted(sub_user_type, super_user_type):
        return jsonify({'res':"", 'err': "新增账户的等级不能高于或等于当前账户！"}), HTTPStatus.BAD_REQUEST
    # 创建子账户
    sub_user = User(_id=id, **data, creator=user_id, extend_data={}).save()

    if not sub_user:
        return jsonify({'res':"", 'err': "create user in mongodb failed"}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'res': "账户新增成功！", 'err': ""}), HTTPStatus.OK

# admin 修改用户
@router_admin.route('/api/admin/modify_user', methods=['PUT'])
@jwt_required()
@access_type_check
@use_args({"_id":fields.Str(required=True),
           "name": fields.Str(), "passwd": fields.Str(),
           "max_devices": fields.Int(), "create_date": fields.Str(), 
           "expire_date": fields.Str(), "department": fields.Str(), 
           "real_name": fields.Str(), "phone": fields.Str(), 
           "creator": fields.Str(), "access_type": fields.Str(), 
           "email": fields.Str(),
           "remark": fields.Str(),
           },
           location="json")
def modify_user(data):
    user_id = get_jwt_identity()
    user = User.objects(_id=data['_id']).first()
    if user is None:
        return jsonify({'res': "", 'err': "所要修改的账户不存在！"}), HTTPStatus.BAD_REQUEST

    # user_name = data.get('name')
    # if not user_name:
    #     return jsonify({'message': "用户名不能为空"}), HTTPStatus.BAD_REQUEST
    # db_user = User.objects(name=user_name).first()
    # if db_user:
    #     return jsonify({'message': "用户名已存在, 不能重复"}), HTTPStatus.BAD_REQUEST

    status = user.update(**data)
    if not status:
        return jsonify({'res': "", 'err': "modify user in mongodb failed"}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'res': "账户修改成功！", 'err': ""}), HTTPStatus.OK

# admin 删除用户
@router_admin.route('/api/admin/delete_user', methods=['DELETE'])
@jwt_required()
@access_type_check
@use_args({"_id":fields.Str(required=True)}, 
           location="json")
def delete_user(data):
    user_id = get_jwt_identity()
    sub_user_id = data['_id']
    try:
        # 从数据库中删除该子账户
        user = User.objects(_id=sub_user_id).first()
        user.delete()
    except Exception as e:
        return jsonify({'res': "", 'err': e}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'res': "账户删除成功！", 'err': ""}), HTTPStatus.OK


# admin 查询用户列表
@router_admin.route('/api/admin/list_user', methods=['GET'])
@jwt_required()
@access_type_check
def list_user():
    user_id = get_jwt_identity()
    res_list = []
    try:
        if user_id == 'admin':
            sub_users = User.objects.filter(Q(creator=user_id) | Q(creator=None))
        else:
            sub_users = User.objects(creator=user_id)
        sub_users = list(sub_users)
        res_list += sub_users
        for user in sub_users:
            if user.access_type == 'admin':
                normal_users = User.objects(creator=user._id)
                res_list.extend(list(normal_users))

        for user in res_list:
            creator = user.creator
            creator_id = creator if creator else 'admin'
            name = User.objects(_id=creator_id).first().name
            user['creator'] = name

    except Exception as e:
        return jsonify({'res': "", 'err': f"query users in mongodb failed: {e}",}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'res': res_list, 'err': ""}), HTTPStatus.OK

@router_admin.route('/api/heartbeat', methods=['POST'])
def receive_heartbeat():
    return {"msg": "heartbeat success"}
