from typing import Union
import os
import sys
from include.config import CommonConfig

os.environ['TZ'] = 'Asia/Shanghai'
# 获取日志根目录
base_path = CommonConfig['LOG_CONFIG']['dir']

# 配置日志输出到文件
folder_ = base_path  # 此处可以自定义路径
name = "context_logger"
rotation_ = "1 day"
retention_ = "30 days"
encoding_ = "utf-8"
backtrace_ = True
diagnose_ = True

from loguru import logger
logger.remove()
loggers_container = {}
def context_logger(context, logger=logger,
                   name="context_logger"):
    global loggers_container
    if not name:
        name = __name__
    if name in loggers_container:
        return loggers_container[name]
    extra_info = ""
    request_id = context.get_request_id()
    if hasattr(context, 'get_session_id'):
        session_id = context.get_session_id()
        extra_info += f"[Session ID: {session_id} Request ID: {request_id}]"
    format_ = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<yellow>{line}</yellow> -' + '<level> {} </level> '.format(
        extra_info) + '<level>{message}</level> '
    logger.add(os.path.join(folder_, name + ".log"), level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
               format=format_, colorize=False,
               rotation=rotation_, retention=retention_, encoding=encoding_,
               enqueue=True, filter=lambda record: record["extra"].get("name") == name)
    logger.add(sys.stderr, level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
               format=format_, colorize=True,
               enqueue=True, filter=lambda record: record["extra"].get("name") == name)
    logger = logger.bind(name=name)
    loggers_container[name] = logger
    return logger

if __name__ == "__main__":
    from include.context import RagQAContext, QueryContext
    # 假设这是你从某处获取的context
    context = RagQAContext(session_id="111")
    context.add_single_question(request_id="222", question_id="333", question="你是谁")
    contextlogger = context_logger(context)
    contextlogger.info('这是一条info级别的日志')
    contextlogger.error('这是一条error级别的日志')
    contextlogger.warning('这是一条warning级别的日志')
