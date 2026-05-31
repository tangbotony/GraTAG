from flask import has_app_context, g, request
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

class ContextualLogger:
    def __init__(self, logger_inst):
        self.logger_inst = logger_inst

    def _log_with_context(self, level, message, *args, **kwargs):
        if has_app_context():
            with self.logger_inst.contextualize(session_id=g.session_id, request_id=g.request_id, user_id=""):
                self.logger_inst.opt(depth=2).log(level, message, *args, **kwargs)
        else:
            self.logger_inst.opt(depth=2).log(level, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._log_with_context("INFO", message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self._log_with_context("DEBUG", message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._log_with_context("WARNING", message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self._log_with_context("ERROR", message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        self._log_with_context("CRITICAL", message, *args, **kwargs)

logger.remove()
loggers_container = {}


def generate_logger(context=None, logger=logger, name="context_logger"):
    global loggers_container
    if not name:
        name = __name__
    if name in loggers_container:
        return update_logger_with_context(loggers_container[name], context)

    format_ = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<yellow>{line}</yellow> | <level> session-id: {extra[session_id]}, request-id: {extra[request_id]}, user-id: {extra[user_id]} </level> | <level>{message}</level>'

    # logger.remove()
    logger.configure(extra={"session_id": "", "request_id": "", "user_id": ""})
    logger.add(os.path.join(folder_, name + ".log"), level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
               format=format_, colorize=False,
               rotation=rotation_, retention=retention_, encoding=encoding_,
               enqueue=True, filter=lambda record: record["extra"].get("name") == name)
    logger.add(sys.stderr, level="DEBUG", backtrace=backtrace_, diagnose=diagnose_,
               format=format_, colorize=True,
               enqueue=True, filter=lambda record: record["extra"].get("name") == name)
    
    logger = update_logger_with_context(logger, context)
    logger = logger.bind(name=name)

    loggers_container[name] = logger
    return logger

def update_logger_with_context(logger, context):
    if context:
        if hasattr(context, 'get_session_id') and context.get_session_id():
            logger = logger.bind(session_id=context.get_session_id())
        if hasattr(context, 'get_request_id') and context.get_request_id():
            logger = logger.bind(request_id=context.get_request_id())
        if hasattr(context, 'get_user_id') and context.get_user_id():
            logger = logger.bind(user_id=context.get_user_id())
    return logger

if __name__ == "__main__":
    from include.context import RagQAContext
    # 假设这是你从某处获取的context
    context = RagQAContext(session_id="111")
    context.add_single_question(request_id="222", question_id="333", question="你是谁", user_id="mock_user_id")
    contextlogger = generate_logger(context)
    contextlogger.info('这是一条info级别的日志')
    contextlogger.error('这是一条error级别的日志')
    contextlogger.warning('这是一条warning级别的日志')