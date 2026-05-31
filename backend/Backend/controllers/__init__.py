import os

import marshmallow
from config import config_manager

# 上传下载文档临时目录
UPLOAD_FILE_DIR = os.path.join(os.path.abspath(os.path.dirname(os.getcwd())), 'llm_tmp')
if not os.path.exists(UPLOAD_FILE_DIR):
    os.makedirs(UPLOAD_FILE_DIR)
# 文档格式转换map
ALLOWED_EXTENSIONS = {'txt': 'plain', 'pdf': 'pdf', 'docx': 'docx', 'doc': 'doc'}
# 支持的上传图片格式
ALLOWED_IMAGE = ["png", "jpg", "jpeg", "gif"]

# 稿件根目录
ROOT_ID = "-1"
ROOT_NAME = "root"

# ai功能
EXPAND_WRITE_NUM = 3
IMAGE_URL = config_manager.controllers_config['IMAGE_URL']
UNKNOW = marshmallow.INCLUDE

import elasticsearch
from elasticsearch import Elasticsearch

es_client = Elasticsearch(hosts=config_manager.es_config['url'], http_auth=(config_manager.es_config['auth'], config_manager.es_config['passwd']))
