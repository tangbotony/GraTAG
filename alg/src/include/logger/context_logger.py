# from typing import Union

# from loguru import logger
# from include.context import RagQAContext, QueryContext
# # from include.context.RagQAContext import RagQAContext
# # from include.context.QueryContext import QueryContext
# from include.utils.text_utils import get_md5
# from include.config import CommonConfig, RagQAConfig
# import os


# os.environ['TZ'] = 'Asia/Shanghai'

# # 获取日志根目录
# base_path = CommonConfig['LOG_CONFIG']['dir']

# # 配置日志输出到文件
# folder_ = base_path # 此处可以自定义路径
# name = "context_logger"
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


# class ContextLogger:
#     def __init__(self, context:Union[RagQAContext.__class__, QueryContext.__class__]):
#         self.logger = logger
#         self.context = context

#     def _get_context_str(self):
#         # 从context中提取request_id和session_id，这里假设它们是context字典的键
#         request_id = self.context.get_request_id()
#         if hasattr(self.context, 'get_session_id'):
#             session_id = self.context.get_session_id()
#             return f"[Session ID: {session_id} Request ID: {request_id}]"
#         return f"Request ID: {request_id}]"

#     def info(self, message):
#         self.logger.info(f"{self._get_context_str()} {message}")

#     def error(self, message):
#         self.logger.error(f"{self._get_context_str()} {message}")

#     def warning(self, message):
#         self.logger.warning(f"{self._get_context_str()} {message}")

# def get_logger(ragContext):
#     # logging.basicConfig(level= level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     # 假设这是你从某处获取的context
#     # 创建一个ContextLogger实例
#     logger = ContextLogger(ragContext)
#     return logger


# # 使用示例
# if __name__ == "__main__":
#     # 假设这是你从某处获取的context
#     context = RagQAContext(session_id=get_md5("XXXX"))
#     context.add_single_question(request_id=get_md5("XXXX-re"),question_id=get_md5("XXXX-qe"),question="你是谁")
#     # 创建一个ContextLogger实例
#     clogger = ContextLogger(context)
#     # 使用封装后的日志方法
#     clogger.info('这是一条info级别的日志')
#     clogger.error('这是一条error级别的日志')
#     clogger.warning('这是一条warning级别的日志')