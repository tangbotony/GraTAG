import os
import sys
from include.config import CommonConfig
from loguru import logger

os.environ['TZ'] = 'Asia/Shanghai'
# 获取日志根目录
base_path = CommonConfig['LOG_CONFIG']['dir']

# 配置日志输出到文件
folder_ = base_path  # 此处可以自定义路径
rotation_ = "1 day"
retention_ = "30 days"
encoding_ = "utf-8"
backtrace_ = True
diagnose_ = True

loggers_container = {}

def general_logger(name):
    global loggers_container
    if name in loggers_container:
        return loggers_container[name]
    logger_inst = logger.bind(name=name, session_id="", request_id="")
    format_ = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> ##｜## <level>{level: <8}</level> ##｜## <cyan>{name}</cyan>:<cyan>{function}</cyan>:<yellow>{line}</yellow> ##｜## <level> session-id: {extra[session_id]}, request-id: {extra[request_id]} </level> ##｜## <level>{message}</level>'
    logger_inst.add(os.path.join(folder_, name + ".log"), level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
               format=format_, colorize=False,
               rotation=rotation_, retention=retention_, encoding=encoding_,
               enqueue=True, filter=lambda record: record["extra"].get("name") == name)
    logger_inst.add(sys.stderr, level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
               format=format_, colorize=True,
               enqueue=True, filter=lambda record: record["extra"].get("name") == name)
    
    loggers_container[name] = logger_inst
    return logger_inst


if __name__ == "__main__":
    timelogger = general_logger(name="time_logger")
    timelogger.info('这是一条info级别的日志')
    timelogger.error('这是一条error级别的日志')
    timelogger.warning('这是一条warning级别的日志')

    algorithmlogger = general_logger(name="algorithm_logger")
    algorithmlogger.info('这是一条info级别的日志', session_id="123", request_id="54354")
    algorithmlogger.error('这是一条error级别的日志', session_id="123", request_id="54354")
    algorithmlogger.warning('这是一条warning级别的日志', session_id="123")
