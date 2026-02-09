import random

from include.context import RagQAContext
from include.logger import ContextLogger
from include.context import RagQAReturnCode
import json
import time
from include.logger import log
from modules.timeline_group.sub_modules import QueryRewrite, EventInfoExtract, Granularity, HighlightExtract, \
    RemoveDuplicatedEvent,ReferenceExtract
from modules.query_division_based_cot_group import QueryDivisionBasedCoTTask
from modules.recall_group import RecallTask
import traceback
import sys
from include.utils.text_utils import get_md5
from include.utils.skywalking_utils import trace_new, start_sw
from include.decorator import timer_decorator
from include.config import PromptConfig, TimeLineConfig
from include.utils.call_white_list import search_whitelist
from include.utils.timeline_utils import get_similarity_whitelist_query,get_dag_query_list
from concurrent.futures import ThreadPoolExecutor

import copy

class TimelineTask:
    """
    全景事件脉络pipeline

    本链路中共包括八个部分(按顺序)：
    - 时间线问题改写模块
    - 意图理解模块
    - 基于CoT的问题拆分模块
    - 多源检索模块
    - 文档级别事件信息抽取模块
    - 事件级别去重模块
    - Highlight提取模块
    - LLM确定脉络生成时间粒度模块
    """

    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)
        self.module_name = "TimelineTask"

    @trace_new(op="get_timeline")
    @timer_decorator
    def get_timeline(self, context=None):
        self.clogger.info("开始时间线梳理！")
        try:
            beginning_time = time.time()
            # 是否开启timeline
            run_timeline = TimeLineConfig["TIMELINE_PIPELINE_PARAMS"]["use_timeline"]
            search_query = self.context.get_origin_question()
            # 校验是否和白名单中query相似
            search_query = get_similarity_whitelist_query(search_query)
            # 检索白名单
            timeline_id = TimeLineConfig["TIMELINE_WHITE_LIST_CONFIG"]["scheme_id"]
            input_info = {"query": search_query}
            timeline_search_res=search_whitelist(scheme_id=timeline_id,input_info=input_info)
            if timeline_search_res and run_timeline:
                timeline_white_res=timeline_search_res[-1]["output"]
                reference_info = json.loads(timeline_white_res["reference"])
                timeline_res = json.loads(timeline_white_res["timeline"])
                sleep_time=random.randint(5,9)
                time.sleep(sleep_time)
                self.context.set_timeline_reference(reference_info)
                self.context.set_timeline_highlight_events(timeline_res)

            else:
                # 时间线query重写
                # QueryRewrite(self.context).get_query_rewrite()
                # new_query=self.context.get_timeline_new_query()
                # 是否使用qa的dag
                use_qa_dag = TimeLineConfig["TIMELINE_PIPELINE_PARAMS"]["use_qa_dag"]
                qa_dag = self.context.get_dag()
                if qa_dag:
                    query_list=get_dag_query_list(qa_dag)
                    # 如果qa没有进行问题增强，则不使用qa的dag
                    if len(query_list) == 1:
                        self.clogger.warning("timeline use self dag! due to qa dag only 1 query")
                        use_qa_dag = False
                    start_time = time.time()
                    while use_qa_dag:
                        # 等待qa的检索结果
                        if self.context.get_recall_finished_flag():
                            if not self.context.get_ref_answer():
                                # qa检索结果为空，则不展示时间线
                                run_timeline = False
                                self.clogger.warning("timeline not run due to qa recall is None!")
                            break
                        if round(time.time()-start_time,2)>TimeLineConfig["TIMELINE_PIPELINE_PARAMS"]["wait_qa_time"]:
                            # qa检索超时则不展示时间线
                            run_timeline = False
                            self.clogger.warning("timeline not run due to qa recall time out!")
                            break
                else:
                    use_qa_dag = False
                    self.clogger.warning("timeline use self dag! due to qa dag is None")
                if run_timeline:
                    new_query = self.context.get_question()
                    self.context.set_timeline_new_query(new_query)
                    if use_qa_dag:
                        self.clogger.warning("timeline use qa dag!")
                        self.context.set_timeline_dag(copy.deepcopy(qa_dag))
                    else:
                        # cot问题拆分
                        QueryDivisionBasedCoTTask(self.context).get_cot(new_query=new_query,use_scene="timeline",split_num_threshold=5)
                        dag = self.context.get_timeline_dag()

                         # 检索召回
                        RecallTask(self.context).get_graph_recall(dag, application="Timeline",
                                                                  top_n_indices= TimeLineConfig["TIMELINE_TASK_PARAMS_CONFIG"]["extract_reference_nums"])
                    # 提取timeline reference
                    ReferenceExtract(self.context).get_timeline_reference(context=self.context)
                    # 时间线事件抽取
                    EventInfoExtract(self.context).get_event_info_extract(context=self.context)

                    with ThreadPoolExecutor(max_workers=2) as executor:
                        # 事件排序和去重
                        RemoveDup_function=RemoveDuplicatedEvent(self.context).get_remove_duplicated_event
                        # 事件粒度确认
                        Granu_function=Granularity(self.context).get_query_granularity
                        executor.submit(RemoveDup_function,self.context)
                        executor.submit(Granu_function,self.context)
                    # 时间线highlight提取
                    HighlightExtract(self.context).get_highlight_extract(context=self.context)
                    # 发送vip信息至飞书群聊
                    time_duration = round(time.time() - beginning_time, 2)
                    timeline_content=copy.deepcopy(self.context.get_timeline_highlight_events())
                    timeline_content.pop("timeline_new_query")
                    timeline_content.pop("cot_split_questions")
                    timeline_content.pop("timeline_sort_events")

            self.clogger.info(
                "timeline_pipeline success, use time {}s".format(round(time.time() - beginning_time, 2)))
            self.clogger.info(f"timeline_res:{self.context.get_timeline_highlight_events()}")
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''

        except Exception as e:

            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_GROUP_ERROR
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
    test_question_list = ["特朗普遭受枪击","习近平2024年行程","今天上海有什么新闻？其中哪些新闻是关于房地产的？" ]
    for i in range(len(test_question_list)):
        session_idx = "mock_session_{}".format(i)
        context = RagQAContext(session_id=get_md5(session_idx))
        context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                    question_id=get_md5("{}_qe".format(session_idx)), question=test_question_list[i])
        context.set_basic_user_info({"User_Date": '123456', "User_IP": '39.99.228.188'})
        response = TimelineTask(context).get_timeline()
        print("context.get_timeline_highlight_events:{}".format(context.get_timeline_highlight_events()))
