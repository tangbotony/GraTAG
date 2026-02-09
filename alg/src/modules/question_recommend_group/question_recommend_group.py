import sys


import time
import json
import traceback

from include.context import QueryContext
from include.context import RagQAReturnCode
from include.logger import ContextLogger
from include.config import QueryReConfig
from include.utils.text_utils import get_md5

from include.utils.db_utils import ESEgine
from include.query.query_recall import get_hotrecall_results
from include.query.query_ranking import get_ranking_reuslts
from include.utils.skywalking_utils import trace_new, record_thread

class QuestionRecommendTask:
    """ 问题推荐 task
        必传入参:
            session_id = context.get_session_id()
    获取本模块执行结果
        - 问题推荐:["习近平何时就职？", "习近平最近访问的国家有哪些?"]
        context.get_recommend_questions()
    """
    def __init__(self, rag_qa_context: QueryContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)
        self.es_engine = ESEgine()

    @trace_new()
    def get_question_recommend(self):
        try:

            beginning_time = time.time()

            # 获取必传入参
            # initialize return info
            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ''
            recall_results = get_hotrecall_results(es_engine=self.es_engine,
                                                   index_name= QueryReConfig["QUERYRECDB"]["ES"]["index_name"], 
                                                   human_label=True, 
                                                   query_field="source.keyword",
                                                   sorted_field="hit_frequency")
            rank_results = get_ranking_reuslts(data=recall_results, 
                                               **QueryReConfig["QUERYRECDB"]["QuestionMainPage"])[:5]
            recommend_questions = [questions[0] for questions in rank_results]
            self.context.set_recommend_questions(recommend_questions=recommend_questions)
            self.clogger.info(
                "get_question_recommend success, use time {}s".format(round(time.time() - beginning_time, 2)))
        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.QUESTION_RECOMMEND_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)

        return {"is_success": is_success,
                "return_code": return_code,
                "detail": error_detail,
                "timestamp": str(time.time()),
                "err_msg": err_msg
                }
    

if __name__ == "__main__":
    test_question_list = [1,2,3,4,5,6]
    for i in range(len(test_question_list)):
        session_idx = "mock_session_{}".format(i)
        context = RagQAContext(session_id=get_md5("main_page"))
        context.add_single_question(request_id=get_md5("main_page_re"),
                                    question_id=get_md5("main_page_qe"), question=None)

        response = QuestionRecommendTask(context).get_question_recommend()
        print(test_question_list[i], response)
        print("context.get_recommend_questions:{}".format(context.get_recommend_questions()))