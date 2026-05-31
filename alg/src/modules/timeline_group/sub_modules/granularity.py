import json
import sys
import time
import traceback

from include.context import RagQAContext, RagQAReturnCode
from include.logger import log, ContextLogger
from include.timeline.granularity import get_granularity
from include.utils import get_md5
from include.utils.skywalking_utils import trace_new, start_sw
from include.decorator import timer_decorator


class Granularity:
    """
    时间粒度生成
    """

    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)

    @trace_new(op='get_query_granularity')
    @timer_decorator
    def get_query_granularity(self, context=None):
        log.info("开始时间线粒度确认模块！")
        try:
            beginning_time = time.time()
            granularity = get_granularity(self.context.get_origin_question(), clogger=self.clogger, session_id=self.context.get_session_id())
            self.context.set_granularity(granularity)
            self.clogger.info(
                "timeline_granularity success, use time {}s".format(round(time.time() - beginning_time, 2))
            )
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''

        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_GRANULARITY_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)
        return json.dumps(
            {
                "is_success": is_success,
                "return_code": return_code,
                "detail": error_detail,
                "timestamp": str(time.time()),
                "err_msg": err_msg
            }, ensure_ascii=False
        )


if __name__ == "__main__":
    start_sw()
    test_question = "请提供一份2024年上半年我国金融统计数据的月度对比分析"
    mock_session_idx = "mock_session_0"
    context = RagQAContext(session_id=mock_session_idx)
    context.add_single_question(request_id=get_md5("{}_re".format(mock_session_idx)),
                                question_id=get_md5("{}_qe".format(mock_session_idx)), question=test_question)
    response = Granularity(rag_qa_context=context).get_query_granularity()
    print("context.get_granularity:{}".format(context.get_granularity()))
