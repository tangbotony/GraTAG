from include.context import RagQAContext
from include.logger import log
from include.logger import ContextLogger
from include.context import RagQAReturnCode
from include.timeline import get_duplicated_sort_event
import traceback
import json
import time
import sys
from include.utils.text_utils import get_md5
from include.utils.Igraph_utils import IGraph, ArcNode
from include.utils.skywalking_utils import trace_new, start_sw
from include.decorator import timer_decorator


class RemoveDuplicatedEvent:
    """
    事件信息去重模块
    必传入参
    question_id = self.context.get_question_id()
    dag=self.context.get_timeline_dag()


    获取本模块执行结果
        - 事件去重排序结果:[{event1},{event2},```]
        context.get_timeline_sort_events()

    """

    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)

    @trace_new(op="get_remove_duplicated_event")
    @timer_decorator
    def get_remove_duplicated_event(self, context=None):
        log.info("开始事件信息去重模块！")
        try:
            assert self.context.get_session_id() is not None, "session_id为空"
            assert self.context.get_request_id() is not None, "request_id为空"
            assert self.context.get_question_id() is not None, "question_id为空"
            assert self.context.get_question() is not None and len(self.context.get_question()) != 0, "question为空"
            assert self.context.get_timeline_dag() is not None, "dag图不为空"

            beginning_time = time.time()
            # 获取必要入参
            dag = self.context.get_timeline_dag()
            question_id = self.context.get_question_id()

            # 获取去重排序后的事件集合
            sort_event_list = get_duplicated_sort_event(dag,context=self.context, clogger=self.clogger)
            # 结果写入context
            self.context.set_timeline_sort_events(sort_event_list, question_id)

            self.clogger.info(
                "timeline_remove_duplicated_event success, use time {}s".format(round(time.time() - beginning_time, 2)))
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''

        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_REMOVE_DUPLICATED_EVENT_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)
        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)


if __name__ == '__main__':
    start_sw()
    test_question = "小米su7走红之路"
    session_idx = "mock_session_0"
    context = RagQAContext(session_id=get_md5(session_idx))
    context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                question_id=get_md5("{}_qe".format(session_idx)), question=test_question)
    event_info1 = [{"事件发生时间": "2024-03-28 xx:xx:xx", "结束时间": "NAN", "事件主体": "小米汽车首款车型SU7",
                    "事件摘要": "2024年3月28日晚，小米汽车首款车型SU7正式上市，锁单量达到75723台。",
                    "事件标题": "小米SU7盛大上市"},
                   {"事件发生时间": "2024-03-29 xx:xx:xx", "结束时间": "2024-03-31 xx:xx:xx", "事件主体": "小米SU7订单增长",
                    "事件摘要": "2024年3月29日至31日，小米SU7订单增长极其狂暴，4分钟破万、7分钟破两万、27分钟破五万。",
                    "事件标题": "小米SU7订单狂暴增长"}]
    event_info2 = [{"事件发生时间": "2024-04-01 xx:xx:xx", "结束时间": "NAN", "事件主体": "小米SU7上市点评",
                    "事件摘要": "2024年4月1日，小米SU7上市点评，突围20万元纯电市场。",
                    "事件标题": "小米SU7突围纯电市场点评"},
                   {"事件发生时间": "2024-04-13 xx:xx:xx", "结束时间": "NAN", "事件主体": "小米SU7营销策略",
                    "事件摘要": "2024年4月13日，小米SU7成功营销背后的策略，包括雷军的人设营销和品牌影响力增强。",
                    "事件标题": "小米SU7营销策略解析"},
                   {"事件发生时间": "2024-04-25 xx:xx:xx", "结束时间": "NAN", "事件主体": "小米SU7在北京国际车展",
                    "事件摘要": "2024年4月25日，小米SU7在北京国际车展上的发布会，宣布锁单量75723台，已交付5781台。",
                    "事件标题": "小米SU7北京车展发布亮点"}]
    dag = IGraph()
    query_1 = "小米su7初步走红"
    query_2 = "小米su7破圈"
    query_3 = "小米汽车"
    x = ArcNode(query_1)
    x2 = ArcNode(query_2)
    x3 = ArcNode(query_3)
    dag.add_new_node(x)
    dag.add_new_node(x2)
    dag.add_new_node(x3)
    dag.add_node_param(query_1, "event_info", event_info1)
    dag.add_node_param(query_2, "event_info", event_info2)
    context.set_timeline_dag(dag, get_md5("{}_qe".format(session_idx)))

    response = RemoveDuplicatedEvent(context).get_remove_duplicated_event()
    print(test_question, response)
    print("context.get_timeline_sort_events:{}".format(context.get_timeline_sort_events()))
