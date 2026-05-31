from include.context import RagQAContext
from include.logger import log
import time
from include.context import RagQAReturnCode
from include.logger import ContextLogger
from include.timeline import get_highlight_events
from include.utils.text_utils import get_md5
from include.utils.skywalking_utils import trace_new, start_sw
import traceback
import sys
import json
from include.decorator import timer_decorator
from include.utils.timeline_utils import get_dag_query_list


class HighlightExtract:
    """
    highlight提取模块
    必传入参
    question_id = self.context.get_question_id()
    timeline_sort_events = self.context.get_timeline_sort_events()


    获取本模块执行结果
        - 事件highlight提取结果:[{event1},{event2},```]
        context.get_timeline_highlight_events()

    """

    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)

    @trace_new(op="get_highlight_extract")
    @timer_decorator
    def get_highlight_extract(self, context=None):
        log.info("开始highlight提取模块！")
        try:
            assert self.context.get_question_id() is not None, "question_id为空"

            # assert len(self.context.get_timeline_sort_events())>0, "事件去重排序结果不为空"

            beginning_time = time.time()
            # 获取必要入参
            question_id = self.context.get_question_id()
            timeline_sort_events = self.context.get_timeline_sort_events()
            granularity = self.context.get_granularity()
            # 获取改写结果
            reference_info = self.context.get_timeline_chunk_reference()
            timeline_highlight_events = get_highlight_events(timeline_sort_events, reference_info,granularity=granularity,
                                                             clogger=self.clogger, session_id=self.context.get_session_id())
            # 结果增加辅助信息
            if self.context.get_timeline_dag():
                new_query = self.context.get_timeline_new_query()
                cot_dag = self.context.get_timeline_dag()
                querylist = get_dag_query_list(cot_dag)
                timeline_highlight_events["timeline_new_query"] = new_query
                timeline_highlight_events["cot_split_questions"] = querylist
                timeline_highlight_events["timeline_sort_events"] = timeline_sort_events
            # 结果写入context
            self.context.set_timeline_highlight_events(timeline_highlight_events, question_id)

            self.clogger.info(
                "timeline_highlight_extract success, use time {}s".format(round(time.time() - beginning_time, 2)))
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''

        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_HIGHLIGHT_EXTRACT_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)
        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)


if __name__ == "__main__":
    start_sw()
    test_question = "中国加入世界贸易组织（WTO）的过程"
    test_timeline_sort_events_str = (
        '[{"事件发生时间": "1986-07-10", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国正式提出恢复其在关贸总协定（GATT，WTO的前身）中的缔约国地位的申请。", "事件标题": "中国提出恢复GATT缔约国申请","url":"www.xxxxxxx.com","chunk_id":"123"},'
        '{"事件发生时间": "1987-03-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国开始与GATT缔约方进行非正式的双边磋商。", "事件标题": "中国与GATT缔约方开始双边磋商","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1989-02-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "由于政治原因，中国加入GATT的谈判进程暂时放缓。", "事件标题": "政治原因导致GATT谈判放缓","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1992-10-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国改革开放政策推动下，中国政府加快了加入GATT的准备工作。", "事件标题": "中国加快加入GATT准备工作","url":"www.xxxxxxx.com","chunk_id":"123"},'
        '{"事件发生时间": "1994-05-xx", "结束时间": "NAN", "事件主体": "GATT", "核心人物": "无", "地点": "无", "事件摘要": "在乌拉圭回合谈判结束时，GATT转变为WTO，中国的谈判对象由GATT转变为WTO。", "事件标题": "乌拉圭回合后GATT转变为WTO","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1995-07-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国与WTO开始正式的双边谈判。", "事件标题": "中国与WTO开始双边谈判","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1997-08-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国与新西兰达成了第一个双边市场准入协议。", "事件标题": "中国与新西兰达成市场准入协议","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1999-11-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "美国和中国就中国加入WTO的条款达成了双边协议，这是中国入世谈判中最重要的双边协议之一。", "事件标题": "中国与美国达成入世双边协议","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2000-05-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "欧盟与中国就中国加入WTO的双边市场准入问题达成一致。", "事件标题": "中国与欧盟达成市场准入一致","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2000-10-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国与加拿大就中国加入WTO达成双边协议。", "事件标题": "中国与加拿大达成入世双边协议","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-06-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国最终完成了与墨西哥的双边市场准入谈判。", "事件标题": "中国与墨西哥完成市场准入谈判","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-09-13", "结束时间": "NAN", "事件主体": "世贸组织中国工作组", "核心人物": "无", "地点": "布鲁塞尔", "事件摘要": "世贸组织中国工作组第18次会议在布鲁塞尔举行，通过了中国加入世贸组织议定书及附件和中国工作组报告书。", "事件标题": "世贸组织中国工作组通过入世议定书","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-11-10", "结束时间": "NAN", "事件主体": "世贸组织", "核心人物": "无", "地点": "多哈", "事件摘要": "在多哈举行的世贸组织第四届部长级会议上，会议审议并通过了中国加入世贸组织的决定。", "事件标题": "世贸组织部长级会议通过中国入世","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-11-11", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国代表签署了中国加入世贸组织议定书。", "事件标题": "中国签署入世议定书","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-12-11", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国正式成为WTO的第143个成员。", "事件标题": "中国正式成为WTO成员","url":"www.xxxxxxx.com","chunk_id":"123"}]')
    test_timeline_sort_events = json.loads(test_timeline_sort_events_str)
    session_idx = "mock_session_0"
    context = RagQAContext(session_id=get_md5(session_idx))
    context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                question_id=get_md5("{}_qe".format(session_idx)), question=test_question)
    context.set_timeline_sort_events(test_timeline_sort_events, question_id=get_md5("{}_qe".format(session_idx)))
    response = HighlightExtract(context).get_highlight_extract()
    print(test_question, response)
    print("无时间粒度信息 context.get_timeline_highlight_events:{}".format(context.get_timeline_highlight_events()))
    context.set_granularity("年")
    response = HighlightExtract(context).get_highlight_extract()
    print(test_question, response)
    print("有时间粒度信息 context.get_timeline_highlight_events:{}".format(context.get_timeline_highlight_events()))
