import datetime
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from controllers import ROOT_ID
from controllers.utils import change_to_meta
from models.delete_file import DeleteFile
from models.document import FILE_TYPE_FOLDER, Document

router_trash = Blueprint('trash', __name__)

# 废纸篓列表
@router_trash.route('/api/trash', methods=['GET'])
@jwt_required()
def list_trash():
    user_id = get_jwt_identity()
    docs = Document.objects(is_trash=True, trash_root=True, user_id=user_id).all()
    meta_list = change_to_meta(docs)
    meta_list.sort()
    meta_list = [item.__dict__ for item in meta_list]
    return jsonify({'message': "", "trash_file": meta_list}), HTTPStatus.OK


# 彻底删除文档
@router_trash.route('/api/trash/document/<id>', methods=['DELETE'])
@jwt_required()
def delete_document(id):
    user_id = get_jwt_identity()
    doc = Document.objects(_id=id, user_id=user_id, is_trash=True, trash_root=True).first()
    if not doc:
        return jsonify({'message': "未在您的文件库中找到该文件 或 您无该篇文档的操作权限"}), HTTPStatus.INTERNAL_SERVER_ERROR
    # 将删除的目录存储在delete数据表
    file = change_to_delete(doc)
    file = file.save()
    if not file:
        return jsonify({'message': "删除该文档{}失败".format(id)}), HTTPStatus.INTERNAL_SERVER_ERROR
    doc.delete()
    return jsonify({'message': "", "doc_id": doc._id}), HTTPStatus.OK


# 恢复文档
@router_trash.route('/api/recover/document/<id>', methods=['GET'])
@jwt_required()
def recover_document(id):
    user_id = get_jwt_identity()
    doc = Document.objects(_id=id, user_id=user_id, is_trash=True).first()
    if not doc:
        return jsonify({'message': "未在您的文件库中找到该文件 或 您无该篇文档的操作权限"}), HTTPStatus.INTERNAL_SERVER_ERROR
    # 如果父目录已被删除，则放在根目录下面
    parent_id = doc.parent_id
    if parent_id != ROOT_ID:
        parent_doc = Document.objects(_id=parent_id, is_trash=False).first()
        if not parent_doc:
            doc.parent_id = ROOT_ID
    status = doc.update(is_trash=False, parent_id=parent_id, trash_root=False)
    return jsonify({'message': "", 'status': status}), HTTPStatus.OK


# 彻底删除目录
@router_trash.route('/api/trash/folder/<id>', methods=['DELETE'])
@jwt_required()
def delete_folder(id):
    user_id = get_jwt_identity()
    fol = Document.objects(_id=id, user_id=user_id, is_trash=True, trash_root=True).first()
    if not fol:
        return jsonify({'message': "未在找到该目录{} 或 您无该目录{}的操作权限".format(id,id)}), HTTPStatus.INTERNAL_SERVER_ERROR
    file = change_to_delete(fol)
    file = file.save()
    fol.delete()
    # 依次删除子目录和子文件夹
    folder_list = [id]
    while folder_list:
        parent_id = folder_list.pop(0)
        docs = Document.objects(parent_id=parent_id, is_trash=True, trash_root=False).all()
        for item in docs:
            if item.type == FILE_TYPE_FOLDER:
                folder_list.append(item._id)
            file = change_to_delete(item)
            file = file.save()
            item.delete()
    return jsonify({'message': "", 'id': id}), HTTPStatus.OK

# 彻底删除全部数据
@router_trash.route('/api/trash/all', methods=['DELETE'])
@jwt_required()
def delete_all():
    user_id = get_jwt_identity()
    fol = Document.objects(user_id=user_id, is_trash=True).all()
    if not fol:
        return jsonify({'message': "您的文件库中无文档 或 无有操作权限的文档"}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    for item in fol:
        file = change_to_delete(item)
        file = file.save()
        item.delete()
    return jsonify({'message': "ok"}), HTTPStatus.OK


# 恢复目录
@router_trash.route('/api/recover/folder/<id>', methods=['GET'])
@jwt_required()
def recover_folder(id):
    fol = Document.objects(_id=id, is_trash=True, trash_root=True).first()
    if not fol:
        return jsonify({'message': "未在找到该目录{} 或 您无该目录{}的操作权限".format(id,id)}), HTTPStatus.INTERNAL_SERVER_ERROR
    parent_id = fol.parent_id
    if parent_id != ROOT_ID:
        parent_doc = Document.objects(_id=id, is_trash=False).first()
        if not parent_doc:
            fol.parent_id = ROOT_ID
    fol.update(is_trash=False, trash_root=False, parent_id=parent_id)
    # 依次恢复子目录和子文件夹
    folder_list = [id]
    while folder_list:
        parent_id = folder_list.pop(0)
        docs = Document.objects(parent_id=parent_id, is_trash=True, trash_root=False).all()
        for item in docs:
            if item.type == FILE_TYPE_FOLDER:
                folder_list.append(item._id)
            item.update(is_trash=False, trash_root=False, parent_id=parent_id)
    return jsonify({'message': "", 'id': id}), HTTPStatus.OK



def change_to_delete(obj):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file = DeleteFile(_id=obj._id, user_id=obj.user_id, name=obj.name, text=obj.text, parent_id=obj.parent_id,
                            type=obj.type, create_time=obj.create_time,
                            update_time=obj.update_time, delete_time=now,
                            history_version=obj.history_version, extend_data=obj.extend_data)
    return file