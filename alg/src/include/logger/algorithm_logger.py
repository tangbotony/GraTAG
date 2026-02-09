# import sys
# from loguru import logger
# from include.config import CommonConfig, RagQAConfig
# import os
# # Configure Loguru's logger at the module level
# # logger.add("./logs/airflow_{time}.log", rotation="1 week", level="DEBUG")





# loggers_container = {}
# LOG_ENABLED = True  # 是否开启日志
# LOG_TO_CONSOLE = True  # 是否输出到控制台
# LOG_FORMAT = '{time:YYYY-MM-DD HH:mm:ss}  | {level} > {elapsed}  | {message}'  # 每条日志输出格式
# LOG_DIR = "./logs/"  # os.path.dirname(os.getcwd())  # 日志文件路径
# LOG_LEVEL = 'DEBUG'  # 日志级别


# os.environ['TZ'] = 'Asia/Shanghai'

# # 获取日志根目录
# base_path = CommonConfig['LOG_CONFIG']['dir']

# # 配置日志输出到文件
# folder_ = base_path # 此处可以自定义路径
# name = "algorithm_logger"
# rotation_ = "1 day"
# retention_ = "30 days"
# encoding_ = "utf-8"
# backtrace_ = True
# diagnose_ = True
# format_ = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> ' \
#             '| <magenta>{process}</magenta>:<yellow>{thread}</yellow> ' \
#             '| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<yellow>{line}</yellow> - <level>{message}</level>'

# logger.add(os.path.join(folder_, name + ".log"), level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
#            format=format_, colorize=False,
#            rotation=rotation_, retention=retention_, encoding=encoding_,
#            enqueue=True, filter=lambda record: record["extra"].get("name") == name)
# logger = logger.bind(name=name)


# def get_logger(name=None):
#     global loggers_container
#     if not name:
#         name = __name__
#     loggers_container[name] = logger
#     if name in loggers_container:
#         return loggers_container[name]
#     return logger


# log = get_logger()