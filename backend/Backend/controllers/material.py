from http import HTTPStatus
from config import config_manager
from multiprocessing import Process
from flask import Blueprint, current_app, jsonify,send_file, request, Response
from webargs import fields
from webargs.flaskparser import use_args
import os
import uuid
from flask_jwt_extended import get_jwt_identity, jwt_required
import requests
from datetime import datetime
import chardet 
# import textract
import traceback
import shutil
import subprocess 
import json

from controllers import UPLOAD_FILE_DIR
from material import (save_obj_to_oss,  read_material_from_oss, 
                                                 save_material_to_es,
                                                 get_file_info_by_id_from_es)
# from material.opt_minio import save_doc_to_minio
from material.opt_oss import save_obj_to_oss, get_oss_env, get_bucket_name
from material import (save_material_to_minio, 
                    read_material_from_minio, 
                    save_material_to_es,
                    get_file_info_by_id_from_es)

from concurrent.futures import ProcessPoolExecutor 
from models.upload_file import UploadDocument

executor_word2pdf = ProcessPoolExecutor(max_workers=1) 

router_material = Blueprint('material', __name__)

ALLOWED_MATERIAL_EXTENSIONS = set(['txt', 'pdf', 'docx', 'doc'])

MATERIAL_OSS_KEY='document'
DOCSEARCH_MATERIAL_OSS_KEY='doc_search'

# 上传素材，支持txt、pdf、doc、docx
@router_material.route('/api/material/upload', methods=['POST'])
@jwt_required()
@use_args({"file": fields.Field(required=True)}, location="files")
def upload_material(data):

    try:
        user_id = get_jwt_identity()
        # user_id = "test_user_id"
        file = data['file']
        if not allowed_file(file.filename):
            return jsonify({'message': "解析失败：只支持txt、doc、docx、pdf文件"}), HTTPStatus.INTERNAL_SERVER_ERROR
    
        material_id = str(uuid.uuid4())
        base_path = os.path.join(UPLOAD_FILE_DIR, "{}_{}".format(user_id, material_id))
        os.makedirs(base_path)

        file_name = file.filename
        ext = file_name.rsplit('.', 1)[1].lower()

        file_saved_name = f"{material_id}.{ext}"
        file_saved = os.path.join(base_path, file_saved_name)
        file.save(file_saved)

        
        try:
            # read content from file
            # text = textract.process(file_saved).decode('utf-8')      
            text = extract_text(file_saved)
            if len(text) < 64:
                return jsonify({'message': "解析失败：文件内容小于64个字符"}), HTTPStatus.LENGTH_REQUIRED
        except Exception as e:
            current_app.logger.error(f"error when reading material, {e}, {traceback.format_exc()}")
            return jsonify({'message': "解析失败：无法读取文件内容"}), HTTPStatus.INTERNAL_SERVER_ERROR
        len_text = len(text)
        obj_key = f"{user_id}/{file_saved_name}"

        # save original file into minio
        # save_material_to_minio(obj_key, file_saved)
        # save original file into oss
        save_obj_to_oss(obj_key, file_saved, MATERIAL_OSS_KEY)

        # change word to pdf for preview in client
        if is_word(ext):
            word_to_pdf(file_saved,base_path)
            pdf_file_saved_name = f"{material_id}.pdf"
            pdf_file_saved = os.path.join(base_path, pdf_file_saved_name)
            pdf_obj_key = f"{user_id}/{pdf_file_saved_name}"
            save_obj_to_oss(pdf_obj_key, pdf_file_saved, MATERIAL_OSS_KEY)


        dt = datetime.now()

        doc = {
            "material_id": material_id,
            "doc_id": material_id,
            "context": text,
            "material_name": file_name,
            "ext": ext,
            "user_id": user_id,
            "raw_file_path": obj_key,
            "insert_time": dt,
            "update_time": dt,
            "status": 0,
            "src_type": 1,
        }

        es_ret= save_material_to_es(material_id, doc)
        current_app.logger.info(f"save to es, id: {material_id}, result: {es_ret}")

        # 删除本地文件
        shutil.rmtree(base_path)

        return jsonify({'message': len_text, 'mid': material_id}), HTTPStatus.OK
    
    except Exception as e:
        current_app.logger.error(f"error when uploading material, {e}, {traceback.format_exc()}")
        return jsonify({'message': f"server error, {e}"}), HTTPStatus.INTERNAL_SERVER_ERROR

"""
对pdf文件进行编码，重复文件不再上传
"""
import subprocess
def get_doc_hash(file_path):
    command = ['md5sum', file_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # 检查命令是否成功执行
    if result.returncode == 0:
        # 解析输出，获取哈希值
        hash_value = result.stdout.decode().split()[0]
        return hash_value
    else:
        # 如果命令执行失败，打印错误信息
        current_app.logger.info(f"Error: {result.stderr.decode()}")
        return None

# 文件上传/重新上传
@router_material.route('/api/doc_search/upload', methods=['POST'])
@jwt_required()
def upload_or_reupload_doc():
    # 获取请求数据，参数&身份校验
    res = {
        "doc_id": "",
        "doc_size": -1,
        "is_empty": False,
        "msg": "",
        "search_doc_id":""
    }
    file = request.files['file']
    user_id = get_jwt_identity()

    # 若已有系列id（追加文件），则可以传过来
    qa_series_id = None
    if 'qa_series_id' in request.form.keys():
        qa_series_id = request.form['qa_series_id']
        res['qa_series_id'] = qa_series_id

    # 解析4种文件类型，并解析出文件大小
    if not allowed_file(file.filename):
        return jsonify({'message': "not allowed file, only support pdf, docx, doc, txt file"}), HTTPStatus.INTERNAL_SERVER_ERROR
    # doc_id = str(uuid.uuid4())
    _id = str(uuid.uuid4())
    res['doc_id'] = _id
    base_path = os.path.join(UPLOAD_FILE_DIR, "{}_{}".format(user_id, _id))
    os.makedirs(base_path)

    try:
        file_name = file.filename
        doc_name = file_name.rsplit('.', 1)[0]
        ext = file_name.rsplit('.', 1)[1].lower()
        file_saved_name = f"{_id}.{ext}"
        file_saved_path = os.path.join(base_path, file_saved_name)
        file.save(file_saved_path)

        doc_id = get_doc_hash(file_saved_path)
        res['search_doc_id'] = doc_id
        doc_size = os.stat(file_saved_path).st_size
        res['doc_size'] = doc_size

        try:
            text = extract_text(file_saved_path)
            if len(text) < 64:
                return jsonify({'message': "解析失败：文件内容小于64个字符"}), HTTPStatus.LENGTH_REQUIRED
            res['is_empty'] = False

        except Exception as e:
            current_app.error(f"error when reading material, {e}, {traceback.format_exc()}")
            return jsonify({'message': "解析失败：无法读取文件内容"}), HTTPStatus.INTERNAL_SERVER_ERROR

    except Exception as e:
        current_app.error(f"error when uploading material, {e}, {traceback.format_exc()}")
        return jsonify({'message': f"server error, {e}"}), HTTPStatus.INTERNAL_SERVER_ERROR

    # 文件对象信息和内容存入mongo
    # save_oss_key = get_oss_env() + DOCSEARCH_MATERIAL_OSS_KEY + "/obj_key"
    bucket_name = get_bucket_name()
    oss_env = get_oss_env()
    save_oss_key = f"oss://{bucket_name}/{oss_env}/{DOCSEARCH_MATERIAL_OSS_KEY}/{user_id}/{doc_id}.{ext}"
    # save_oss_key = f"{get_oss_env()}/{DOCSEARCH_MATERIAL_OSS_KEY}/{user_id}/{doc_id}"

    
    """
    预留方案，之后如果需要节省资源，可以添加此逻辑
    判定pdf是否已经过解析上传
    pdf_upload_flag = UploadDocument.objects(doc_id=doc_id).first()
    if not pdf_upload_flag:
    """
    uploadDocument = UploadDocument(_id=_id, doc_id=doc_id, user_id=user_id, name=doc_name, format=ext, 
               create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               qa_series_id=qa_series_id if qa_series_id else "",
               size=doc_size, selected=True,
               text=text, obj_key=save_oss_key
               ).save()
    obj_key = ""
    oss_file_saved_name = f"{doc_id}.{ext}"
    obj_key = f"{user_id}/{oss_file_saved_name}"
    save_obj_to_oss(obj_key, file_saved_path, OSS_KEY=DOCSEARCH_MATERIAL_OSS_KEY)
    shutil.rmtree(base_path)
    # 开启一个独立的进程
    request_id = request.headers.get('X-Request-Id')
    session_id = qa_series_id

    processes = []
    # process_mode = ['doc_pro', 'doc']
    process_mode = ['doc']
    for mode in process_mode:
        process = Process(target=aync_analyse, args=(save_oss_key, user_id, request_id, session_id, _id, ext, mode))
        processes.append(process)
        process.start()

    # for process in processes:
    #     process.join()
    
    current_app.logger.info(f"save to mongo, id: {doc_id}, result: {uploadDocument}")

    res['msg'] = "文件上传成功！"
    return jsonify(res), HTTPStatus.OK

def aync_analyse(oss_id, user_id, request_id, session_id, doc_id, ext, mode):
    algorithm_url = config_manager.default_config['ALGORITHM_URL']
    url = f"{algorithm_url}/execute"
    payload = json.dumps({
        "_ids": [doc_id],
        "oss_ids": [oss_id],
        "types": [ext],
        "user_id": user_id,
        "mode" : mode
    })
    headers = {
        'request-id': 'test',
        'session-id': 'test',
        'function': 'extract_pdf',
        'Content-Type': 'application/json'
    }
    headers["request-id"] = request_id
    headers["session-id"] = session_id
    res = requests.request("POST", url, headers=headers, data=payload)
    if res.status_code == 200: # 若解析成功，执行数据库更新操作
        uploadDocument = UploadDocument.objects(_id=doc_id).first()
        if mode == "doc":
            uploadDocument.analysed = True
            uploadDocument.pre_cot = True
            uploadDocument.save()
        else:
            uploadDocument.analysed_pro = True
            uploadDocument.save()
    if ext == 'txt':
        uploadDocument = UploadDocument.objects(_id=doc_id).first()
        uploadDocument.pre_cot = True
        uploadDocument.save()


@router_material.route('/api/material/<mid>', methods=['GET'])
@jwt_required()
def get_material_info(mid):

    try:
        # user_id = get_jwt_identity()
        # user_id = "test_user_id"

        file_info = get_file_info_by_id_from_es(mid)
        if not file_info:
            return jsonify({'message': f"找不到文件：{mid}"}), HTTPStatus.INTERNAL_SERVER_ERROR
        return jsonify({'message': "", 'result': file_info}), HTTPStatus.OK  
    
    except Exception as e:
        current_app.logger.error(f"error when getting material [{mid}], {e}, {traceback.format_exc()}")
        return jsonify({'message': f"server error, {e}"}), HTTPStatus.INTERNAL_SERVER_ERROR




@router_material.route('/api/material/preview/<mid>', methods=['GET'])
@jwt_required()
def preview_material(mid):

    try:
        user_id = get_jwt_identity()
        # user_id = "test_user_id"

        to_pdf = "to_pdf" in request.args

        try:
            file_info = get_file_info_by_id_from_es(mid)
            # if not file_info:
            #     return jsonify({'message': f"找不到文件：{mid}"}), HTTPStatus.INTERNAL_SERVER_ERROR
            ext = file_info['ext']
            file_name = file_info['material_name']
            obj_key = file_info['raw_file_path']
            if to_pdf and is_word(ext):
                obj_key = ext_to_pdf(ext, obj_key)
                file_name = ext_to_pdf(ext, file_name)
                ext = "pdf"
        except:
            file_name = f'{mid}.pdf'
            obj_key = f'{user_id}/{mid}.pdf'
            ext = "pdf"
        data_stream = read_material_from_oss(obj_key, MATERIAL_OSS_KEY)        
        content_type = get_content_type(ext)
        if ext.lower() == "txt":
            detected_encoding = chardet.detect(data_stream.getvalue())['encoding']
            data_stream = data_stream.getvalue().decode(detected_encoding, errors='replace')
            return Response(data_stream, content_type='text/plain; charset=utf-8')

        return send_file(  
            data_stream,  
            as_attachment=False,  # 如果希望文件被下载而不是在浏览器中打开，可以设置为 True  
            download_name=file_name,  # 设置下载的文件名  
            mimetype=content_type 
        )       
    
    except Exception as e:
        current_app.logger.error(f"error when previewing material [{mid}], {e}, {traceback.format_exc()}")
        return jsonify({'message': f"server error, {e}"}), HTTPStatus.INTERNAL_SERVER_ERROR




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_MATERIAL_EXTENSIONS

def get_content_type(ext):
    if ext == 'pdf':  
        return 'application/pdf'  
    elif ext == 'doc':  
        return 'application/msword'  
    elif ext == 'docx':  
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'  
    elif ext == 'txt':  
        return 'text/plain'
    else:
        return 'application/octet-stream'
    

CUR_FILE = os.path.abspath(__file__) 
JAR_FILE= os.path.join( os.path.dirname(os.path.dirname(CUR_FILE)),"file/tika-app-2.9.2.jar")

def extract_text(file_path):
    command = ["java", "-jar", JAR_FILE, "-t", file_path]
    result = subprocess.run(command, capture_output=True, text=True) 
    if result.returncode == 0:  
        return result.stdout
    else:  
        current_app.logger.error(f"error when extracting text from file {file_path}, error code: {result.returncode}, error: {result.stderr}")
        raise Exception(result.stderr)

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True) 
    return {
        'stdout': result.stdout,  
        'stderr': result.stderr,  
        'returncode': result.returncode  
    }
        
def word_to_pdf(file_path, out_dir):
    try:
        command = ["libreoffice", "--headless", "--convert-to", "pdf","--outdir", out_dir, file_path ]     
        future = executor_word2pdf.submit(run_cmd, command)   
        ret = future.result()
        current_app.logger.info(f"word to pdf from file {file_path}, result: {ret}")
        if ret['returncode'] == 0:
            return ret
        else:
            current_app.logger.error(f"error when changing word to pdf from file {file_path}, result: {ret}")
            raise Exception(ret['stderr'])
    except Exception as e:
        raise e 
         
    
def is_word(ext):
    return  (ext == 'doc' or ext == 'docx')

def ext_to_pdf(ext, full_name):
    return os.path.splitext(full_name)[0] + '.pdf'
