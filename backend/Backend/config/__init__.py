import configparser
import os
from config import logger
from config.logger import Logger
import os
from  pyapollo.apollo_client import ApolloClient
import nacos
import json
path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
config = configparser.ConfigParser()
final_path = os.path.join(path, 'config/config_local.ini')
config.read(final_path)

# # Apollo客户端
# try:
#     # 读取apollo相关配置文件
#     path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
#     config = configparser.ConfigParser()
#     final_path = os.path.join(path, 'config/apollo_config.ini')
#     config.read(final_path)
#     apollo_config = config['APOLLO']
#     # 连接apollo服务端
#     apollo_client = ApolloClient(
#         app_id = apollo_config['app_id'],
#         cluster = apollo_config['cluster'],
#         cache_file_path = apollo_config['cache_file_path'],
#         config_server_url = apollo_config['config_server_url'],
#         authorization = apollo_config['authorization'],
#         env = apollo_config['env']
#     )
#     apollo_client.start()



#     # 获取Apollo配置，以字典形式存储
#     default_config = {
#         'Host': apollo_client.get_value('default.Host'),
#         'Port': apollo_client.get_value('default.Port'),
#         'LOG_DIR': apollo_client.get_value('default.LOG_DIR'),
#         'TOKEN_KEY': apollo_client.get_value('default.TOKEN_KEY'),
#         'SIMILARITY_URL': apollo_client.get_value('default.SIMILARITY_URL'),
#         'SIMILARITY_TOKEN': apollo_client.get_value('default.SIMILARITY_TOKEN'),
#         'ALGORITHM_URL': apollo_client.get_value('default.ALGORITHM_URL'),
#         'ALGORITHM_2_URL': apollo_client.get_value('default.ALGORITHM_2_URL')
#     }

#     # 其他配置项
#     mongo_config = {
#         'Host': apollo_client.get_value('mongo.Host'),
#         'Port': apollo_client.get_value('mongo.Port'),
#         'DB': apollo_client.get_value('mongo.DB'),
#         'Username': apollo_client.get_value('mongo.Username'),
#         'Password': apollo_client.get_value('mongo.Password'),
#         'authDB': apollo_client.get_value('mongo.authDB')
#     }

#     controllers_config = {
#         'IMAGE_URL' : apollo_client.get_value('CONTROLLERS.IMAGE_URL')
#     }

#     tapd_config = {
#         'auth' : apollo_client.get_value('TAPD.auth'),
#         'key' : apollo_client.get_value('TAPD.key'),
#         'task_url' : apollo_client.get_value('TAPD.task_url'),
#         'project_feedback_project_id' : apollo_client.get_value('TAPD.project_feedback_project_id'),
#         'project_owner' : apollo_client.get_value('TAPD.project_owner'),
#         'content_feedback_project_id' : apollo_client.get_value('TAPD.content_feedback_project_id'),
#         'content_owner' : apollo_client.get_value('TAPD.content_owner')
#     }

#     monitor_config = {
#         'enable' : apollo_client.get_value('MONITOR.enable'),
#         'url' : apollo_client.get_value('MONITOR.url')
#     }

#     es_config = {
#         'url': apollo_client.get_value('ES.url'),
#         'auth': apollo_client.get_value('ES.auth'),
#         'passwd': apollo_client.get_value('ES.passwd'),
#         'search_index': apollo_client.get_value('ES.search_index')
#     }

#     prometheus_config = {
#         'enable_flask': apollo_client.get_value('PROMETHEUS.enable_flask'),
#         'process_name': apollo_client.get_value('PROMETHEUS.process_name')
#     }

#     minio_config = {
#         'url': apollo_client.get_value('MINIO.url'),
#         'access_key': apollo_client.get_value('MINIO.access_key'),
#         'secret_key': apollo_client.get_value('MINIO.secret_key')
#     }
#     # 非[]后的配置项可以直接写成一个值
#     alg_tmp_url = apollo_client.get_value('ALG_TMP.url')
#     baidu_config = {
#         'url' : apollo_client.get_value('BAIDU.url')
#     }

# # 异常捕捉，使用原始读取配置文件的方法
# except Exception as e:
#     print(f"An unexpected error occurred: {e}")
#     # 配置文件读取
#     path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
#     config = configparser.ConfigParser()
#     final_path = os.path.join(path, 'config/config.ini')
#     config.read(final_path)
#     # 保证配置名一样，都是分割成字典
#     default_config = config['DEFAULT']
#     mongo_config = config['MONGO']
#     controllers_config = config['CONTROLLERS']
#     tapd_config = config['TAPD']
#     monitor_config = config['MONITOR']
#     baidu_config = config['BAIDU']
#     es_config = config['ES']
#     minio_config = config['MINIO']
#     prometheus_config = config['PROMETHEUS']
#     alg_tmp_url = config['ALG_TMP']['url']

# def update_config():
#     global default_config, mongo_config
#     default_config = {
#         'Host': apollo_client.get_value('default.Host'),
#         'Port': apollo_client.get_value('default.Port'),
#         'LOG_DIR': apollo_client.get_value('default.LOG_DIR'),
#         'TOKEN_KEY': apollo_client.get_value('default.TOKEN_KEY'),
#         'SIMILARITY_URL': apollo_client.get_value('default.SIMILARITY_URL'),
#         'SIMILARITY_TOKEN': apollo_client.get_value('default.SIMILARITY_TOKEN'),
#         'ALGORITHM_URL': apollo_client.get_value('default.ALGORITHM_URL'),
#         'ALGORITHM_2_URL': apollo_client.get_value('default.ALGORITHM_2_URL')
#     }
#     mongo_config = {
#         'Host': apollo_client.get_value('mongo.Host'),
#         'Port': apollo_client.get_value('mongo.Port'),
#         'DB': apollo_client.get_value('mongo.DB'),
#         'Username': apollo_client.get_value('mongo.Username'),
#         'Password': apollo_client.get_value('mongo.Password'),
#         'authDB': apollo_client.get_value('mongo.authDB')
#     }

# default_config, mongo_config, controllers_config, tapd_config, monitor_config, \
#         baidu_config, es_config, minio_config, prometheus_config, alg_tmp_url = None

class ConfigManager:
    def __init__(self):
        self.default_config = None
        self.mongo_config = None
        self.controllers_config = None
        self.baidu_config = None
        self.es_config = None
        self.minio_config = None
        self.prometheus_config = None
        self.alg_tmp_url = None
        self.oss_config = None

    def refresh_config(self, config):
        self.default_config = config.get('default')
        self.mongo_config = config.get('mongo')
        self.controllers_config = config.get('CONTROLLERS')
        self.es_config = config.get('ES')
        self.prometheus_config = config.get('PROMETHEUS')
        self.minio_config = config.get('MINIO')
        self.alg_tmp_url = config.get('ALG_TMP', {}).get('url')
        self.baidu_config = config.get('BAIDU')
        self.oss_config = config.get('OSS')

    def refresh_config_local(self, config):
        self.default_config = config['DEFAULT']
        self.mongo_config = config['MONGO']
        self.controllers_config = config['CONTROLLERS']
        self.es_config = config['ES']
        self.prometheus_config = config['PROMETHEUS']
        self.minio_config = config['MINIO']
        self.alg_tmp_url = config['ALG_TMP']['url']
        self.baidu_config = config['BAIDU']
        self.oss_config = config['OSS']


def init_config_from_local(config_manager):
    path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    config = configparser.ConfigParser()
    final_path = os.path.join(path, 'config/config.ini')
    config.read(final_path)
    config_manager.refresh_config_local(config)

# 读取 nacos 服务端数据，并初始化当前的服务的配置
def init_config_from_nacos(config_manager, client, data_id, group):
    config = client.get_config(data_id, group)
    config = json.loads(config)
    config_manager.refresh_config(config)
    # client.add_config_watcher(data_id, group, config_change_callback)

def init_nacos_config():
    path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    config = configparser.ConfigParser()
    final_path = os.path.join(path, 'config/nacos_config.ini')
    config.read(final_path)
    nacos_config = config['NACOS']
    return nacos_config

# TODO
def config_change_callback(config):
    pass


config_manager = ConfigManager()
# 初始化 nacos 的配置
nacos_client = None
nacos_config = init_nacos_config()
if nacos_config.get('LOCAL_CONFIG') == 'true':
    init_config_from_local(config_manager)
else:
    # 初始化 nacos 的客户端，并从nacos 服务端读取配置数据
    nacos_client = nacos.NacosClient(nacos_config['SERVER_ADDRESSES'], namespace=nacos_config['NAMESPACE'], 
                                     ak=nacos_config['AK'], sk=nacos_config['SK'], logDir=nacos_config['LOG_DIR'])
    init_config_from_nacos(config_manager, nacos_client, nacos_config['DATA_ID'], nacos_config['GROUP'])
print(config_manager.__dict__)


log_path = config_manager.default_config['LOG_DIR']
if not os.path.exists(log_path):
    os.makedirs(log_path)

monitor_log=logger.Logger(os.path.join(log_path, 'monitor.log'), level='info')
default_log = logger.Logger.get_app_hander(os.path.join(log_path, 'app.log'), level='info')
alg_log = logger.Logger(os.path.join(log_path, 'alg.log'), level='info')
engine_log = logger.Logger(os.path.join(log_path, 'engine.log'), level='info')
llm_log = logger.Logger(os.path.join(log_path, 'llm.log'),level='info')
logging = Logger(os.path.join(log_path, 'material.log'), level='info')
response_log = Logger(os.path.join(log_path, 'response.log'), level='info')
