import datetime
import uuid
from http import HTTPStatus

from controllers.utils import change_to_meta, get_path, validator_parent_id
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.document import FILE_TYPE_FOLDER, Document
from webargs import fields
from webargs.flaskparser import use_args

router_folder = Blueprint('folder', __name__)

# 新建目录
@router_folder.route('/api/folder', methods=['POST'])
@jwt_required()
@use_args({"name": fields.Str(required=True), "parent_id": fields.Str(required=True)}, location="json")
def create_folder(data):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = get_jwt_identity()
    id = str(uuid.uuid4())
    name, parent_id = data.get('name'), data.get("parent_id")
    path = get_path(parent_id, id, name, user_id)

    folder = Document(_id=id, user_id=user_id, name=name, parent_id=parent_id, text="", type=FILE_TYPE_FOLDER,
                    path=path, create_time=now, update_time=now).save()  
    if not folder:
        return jsonify({'message': "create folder in mongodb failed"}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'message': "", 'folder_id': folder._id}), HTTPStatus.OK


# 删除目录
@router_folder.route('/api/folder/<id>', methods=['DELETE'])
@jwt_required()
def trash_folder(id):
    user_id = get_jwt_identity()
    folder = Document.objects(_id=id, user_id=user_id, is_trash=False, is_delete=False).first()
    if not folder:
        return jsonify({'message': "未在找到该目录{} 或 您无该目录{}的操作权限".format(id,id)}), HTTPStatus.INTERNAL_SERVER_ERROR
    trash_time = datetime.datetime.now() + datetime.timedelta(days=30)
    trash_time = trash_time.strftime("%Y-%m-%d %H:%M:%S")
    status = folder.update(is_trash=True, trash_time=trash_time, trash_root=True)

    # 依次删除子目录和子文件
    folder_list = [id]
    while folder_list:
        parent_id = folder_list.pop(0)
        docs = Document.objects(parent_id=parent_id, is_trash=False, is_delete=False).all()
        for item in docs:
            if item.type == FILE_TYPE_FOLDER:
                folder_list.append(item._id)
            status = item.update(is_trash=True, trash_time=trash_time) and status
    return jsonify({'message': "", 'status': status}), HTTPStatus.OK


# 更新目录
@router_folder.route('/api/folder', methods=['PUT'])
@jwt_required()
@use_args({"id": fields.Str(required=True), "name": fields.Str(), 
           "parent_id": fields.Str()}, location="json")
def update_folder(data):
    user_id = get_jwt_identity()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    folder = Document.objects(_id=data["id"], user_id=user_id, is_trash=False, is_delete=False).first()
    if not folder:
        return jsonify({'message': "未在找到该目录{} 或 您无该目录{}的操作权限".format(data["id"],data["id"])}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    # parent id校验
    if "parent_id" in data:
        if not validator_parent_id(data.get("parent_id"), user_id):
            return jsonify({'message': "not found parent id in database"}), HTTPStatus.BAD_REQUEST
        path = get_path(data.get("parent_id"), data["id"], folder.name, user_id)
        data['path'] = path

    data['update_time'] = now
    data.pop("id") 
    status = folder.update(**data)
    return jsonify({'message': "", 'status': status}), HTTPStatus.OK


# 查询目录
@router_folder.route('/api/folder/<id>', methods=['GET'])
@jwt_required()
def list_folder(id):
    user_id = get_jwt_identity()
    document = Document.objects(parent_id=id, user_id=user_id, is_trash=False, is_delete=False).all()
    meta_list = change_to_meta(document)
    meta_list.sort()
    meta_list = [item.__dict__ for item in meta_list]
    return jsonify({'message': "", 'meta': meta_list}), HTTPStatus.OK
