from config import config_manager
from io import BytesIO 
import oss2

class OssPipeline(object):
    def __init__(self, endpoint, access_key_id, access_key_secret, bucket_name):
        # 创建oss连接对象
        self.endpoint = endpoint
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.bucket_name = bucket_name
        self.region = 'cn-shanghai'  # V4版本新增region
        # 使用V4版本验证方式
        self.auth = oss2.AuthV4(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name, region=self.region)
    def save_oss(self, oss_id, data):
        self.bucket.put_object(oss_id, data) 
    def get_oss(self, oss_id):
        return self.bucket.get_object(oss_id)
    def del_oss(self, oss_id):
        return self.bucket.delete_object(oss_id)
    
oss_client = OssPipeline(config_manager.oss_config['endpoint'], config_manager.oss_config['access_key_id'], 
                     config_manager.oss_config['access_key_secret'], config_manager.oss_config['bucket_name'])
                    #  config_manager.oss_config['access_key_secret'], "public-pdf-extract-kit")

oss_client_img = OssPipeline(config_manager.oss_config['endpoint'], config_manager.oss_config['access_key_id'], 
                     config_manager.oss_config['access_key_secret'], config_manager.oss_config['img_bucket'])

def get_oss_env():
    return config_manager.oss_config['oss_env']

def get_bucket_name():
    return config_manager.oss_config['bucket_name']

 # 直接写入txt 传入oss
def save_obj_to_oss(object_key, file_path, OSS_KEY):
    # 读取文件内容到BytesIO对象中  
    with open(file_path, "rb") as file_data:  
        file_content = BytesIO(file_data.read())  
    oss_id = object_key
    # 上传文件到oss  
    oss_client.save_oss(f"{config_manager.oss_config['oss_env']}/{OSS_KEY}/{oss_id}", file_content)  

def save_img_to_oss(object_key, file_content, OSS_KEY):
    oss_id = object_key
    # 上传文件到oss  
    oss_client_img.save_oss(f"{OSS_KEY}/{oss_id}", file_content) 

def read_obj_from_oss(object_key):
    # 从 oss 读取文件  
    response = oss_client.get_oss(object_key)  
    # 将文件内容存储在 BytesIO 缓冲区中  
    data = BytesIO()  
    for chunk in response:  
        data.write(chunk)  
    data.seek(0)  # 将文件指针重置到开头  
    return data

def read_material_from_oss(object_key, OSS_KEY):
    return read_obj_from_oss(object_key=f"{config_manager.oss_config['oss_env']}/{OSS_KEY}/{object_key}")

def read_material_from_oss_v2(object_key):
    return read_obj_from_oss(object_key=object_key)

def delete_obj_from_oss(oss_id):
    oss_client.del_oss(oss_id)
    return "文件删除成功!"

def delete_material_from_oss(object_key, OSS_KEY):
    return delete_obj_from_oss(oss_id=f"{config_manager.oss_config['oss_env']}/{OSS_KEY}/{object_key}")