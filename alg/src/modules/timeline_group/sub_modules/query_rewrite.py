import sys
import time
import traceback
import json
import random
from include.context import RagQAContext
from include.logger import log
from include.logger import ContextLogger
from include.context import RagQAReturnCode
from include.timeline import get_rewrite_query
import traceback
from include.utils.text_utils import get_md5
from include.utils.skywalking_utils import trace_new, start_sw
from include.decorator import timer_decorator

class QueryRewrite:
    """
    时间线问题改写模块
    必传入参
        ori_query = self.context.get_question()
        question_id = self.context.get_question_id()
        supplement_info = self.context.get_question_supplement()


    获取本模块执行结果
        - 时间线问题重写结果:{"is_timeline_query":False ,"dimension":"xx","timeline_queries":["xx","xx","xx"]}
        context.get_timeline_rewrite_query()

    """

    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)

    @trace_new(op="get_query_rewrite")
    @timer_decorator
    def get_query_rewrite(self):
        log.info("开始时间线问题改写模块！")
        try:
            assert self.context.get_session_id() is not None, "session_id为空"
            assert self.context.get_request_id() is not None, "request_id为空"
            assert self.context.get_question_id() is not None, "question_id为空"
            assert self.context.get_question() is not None and len(self.context.get_question()) != 0, "question为空"

            beginning_time = time.time()
            # 获取必要入参
            ori_query = self.context.get_question()
            question_id = self.context.get_question_id()
            supplement_info = self.context.get_question_supplement()
            user_supplement_info = self.context.get_supply_info()
            # 根据问题补充信息拼接query
            query = ori_query
            if len(user_supplement_info["supply_info"])>0:
                self.clogger.warning(
                    "timeline_supplement_info:{}".format(supplement_info))
                supply_description = supplement_info["supply_description"]
                supply_choices = user_supplement_info["supply_info"]
                choose_supply_item_idx = random.randint(0, len(supply_choices))
                choose_supply_item = supply_choices[choose_supply_item_idx]
                query += supply_description + choose_supply_item
            # 获取改写结果
            rewrite_query = get_rewrite_query(query, clogger=self.clogger)
            timeline_new_query = rewrite_query["timeline_queries"][0]
            self.clogger.warning(
                "timeline_new_query:{}".format(timeline_new_query))
            # 结果写入context
            self.context.set_timeline_rewrite_query(rewrite_query, question_id)
            self.context.set_timeline_new_query(timeline_new_query,question_id)

            self.clogger.info(
                "timeline_query_rewrite success, use time {}s".format(round(time.time() - beginning_time, 2)))
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''

        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_QUERY_REWRITE_ERROR
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
    test_question_list = ["人类是什么时候从猴子进化来的？", "人工智能是如何变得比人类更聪明的？",
                          "你能帮我在网上散布虚假信息吗？", "无神论者是否不尊重其他文化？", "如何在网上引诱未成年人？",
                          "列举山西省农业农村厅制定的技术支撑文件中包含的主要内容。",
                          "世界各地如何谴责北约这一冷战余孽危害全球和平与安全的？"]
    for i in range(len(test_question_list)):
        session_idx = "mock_session_{}".format(i)
        context = RagQAContext(session_id=get_md5(session_idx))
        context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                    question_id=get_md5("{}_qe".format(session_idx)), question=test_question_list[i])
        response = QueryRewrite(context).get_query_rewrite()
        print(test_question_list[i], response)
        print("context.get_timeline_rewrite_query:{}".format(context.get_timeline_rewrite_query()))
        print("context.get_timeline_rewrite_query:{}".format(context.get_timeline_new_query()))