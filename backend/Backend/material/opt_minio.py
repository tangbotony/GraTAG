from config import config_manager
from minio import Minio
from minio.error import S3Error
from io import BytesIO 

MINIO_BUCKET_NAME_MATERIAL="material"
MINIO_BUCKET_NAME_DOCSEARCH="docsearch"

minio_client = Minio(config_manager.minio_config['url'], 
                     access_key=config_manager.minio_config['access_key'], 
                     secret_key=config_manager.minio_config['secret_key'],  
                     secure=False)


def save_obj_to_minio(bucket_name, object_key, file_path):
    if not minio_client.bucket_exists(bucket_name):  
        minio_client.make_bucket(bucket_name)
    
    # 读取文件内容到BytesIO对象中  
    with open(file_path, "rb") as file_data:  
        file_content = BytesIO(file_data.read())  
  
    # 上传文件到MinIO  
    minio_client.put_object(bucket_name, object_key, file_content, file_content.getbuffer().nbytes)  


def save_material_to_minio(object_key, file_path): 
    save_obj_to_minio(MINIO_BUCKET_NAME_MATERIAL,object_key,file_path)

def save_doc_to_minio(object_key, file_path): 
    save_obj_to_minio(MINIO_BUCKET_NAME_DOCSEARCH,object_key,file_path)

def read_obj_from_minio(bucket_name, object_key):
    
    # 从 MinIO 读取文件  
    response = minio_client.get_object(bucket_name, object_key)  

    # 将文件内容存储在 BytesIO 缓冲区中  
    data = BytesIO()  
    for chunk in response:  
        data.write(chunk)  
    data.seek(0)  # 将文件指针重置到开头  
    return data

def read_material_from_minio(object_key):
    return read_obj_from_minio(MINIO_BUCKET_NAME_MATERIAL,object_key=object_key)

def read_doc_from_minio(object_key):
    return read_obj_from_minio(MINIO_BUCKET_NAME_DOCSEARCH, object_key=object_key)

def delete_obj_from_minio(bucket_name, object_key):
    try:
        minio_client.remove_object(bucket_name, object_key)
        return "文件删除成功!"
    except S3Error as e:
        return f"文件删除异常: {e}"

def delete_doc_from_minio(object_key):
    return delete_obj_from_minio(MINIO_BUCKET_NAME_DOCSEARCH, object_key=object_key)
