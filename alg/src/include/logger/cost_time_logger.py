# import sys
# from loguru import logger
# import datetime
# from include.config import CommonConfig, RagQAConfig
# import os

# os.environ['TZ'] = 'Asia/Shanghai'

# # 获取日志根目录
# base_path = CommonConfig['LOG_CONFIG']['dir']

# # 配置日志输出到文件
# folder_ = base_path # 此处可以自定义路径
# name = "time_log"
# rotation_ = "1 day"
# retention_ = "30 days"
# encoding_ = "utf-8"
# backtrace_ = True
# diagnose_ = True


# format_ = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> ##|## <level>{level: <8}</level> ' \
#             '##|## <magenta>{process}</magenta>:<yellow>{thread}</yellow> ' \
#             '##|## <cyan>{name}</cyan>:<cyan>{function}</cyan>:<yellow>{line}</yellow> ##|## <level>{message}</level>'

# logger.add(os.path.join(folder_, name + ".log"), level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
#            format=format_, colorize=False,
#            rotation=rotation_, retention=retention_, encoding=encoding_,
#            enqueue=True, filter=lambda record: record["extra"].get("name") == name)
# time_log = logger.bind(name=name)



