from __future__ import annotations


# from include.logger.opt_context_logger import context_logger as ContextLogger
# from include.logger.general_logger import general_logger
# pipeline_log = general_logger(name="pipeline_logger")
# time_log = general_logger(name="time_logger")
# log = general_logger(name="algorithm_logger")
# context_log = general_logger(name="context_new_logger")
"""
在子线程中打印日志，需要传递context上下文信息，不然日志中无法获取session_id和request_id，无法进行链路追踪
使用样例:
class QueryRecommendTask:
    def __init__(self, rag_qa_context: QueryContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)
"""
from include.logger.ainews_logger import generate_logger as ContextLogger
pipeline_log = ContextLogger(name="pipeline_logger")
time_log = ContextLogger(name="time_logger")
log = ContextLogger(name="algorithm_logger")
context_log = ContextLogger(name="context_new_logger")

# from include.logger.algorithm_logger import log
# from include.logger.context_logger import ContextLogger
# from include.logger.pipeline_logger import pipeline_log
# from include.logger.cost_time_logger import time_log
