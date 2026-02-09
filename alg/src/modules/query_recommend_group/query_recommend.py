import sys
import time
import json
import traceback
from include.context import QueryContext
from include.context import RagQAReturnCode
from include.logger import ContextLogger
from include.config import QueryReConfig
from include.utils.text_utils import get_md5

from include.utils.db_utils import ESEgine, MilvusEngine
from include.query.query_recall import get_recall_results
from include.query.query_ranking import get_ranking_reuslts
from include.utils.skywalking_utils import trace_new
from include.utils.call_white_list import search_whitelist

class QueryRecommendTask:
    """ 问题推荐 task
        必传入参:
            session_id = context.get_session_id()
            request_id = context.get_request_id()
            question_id = context.get_question_id()
            question = context.get_question()
    获取本模块执行结果
        - 问题推荐:["习近平何时就职？", "习近平最近访问的国家有哪些?"]
        context.get_recommend_questions()
    """
    def __init__(self, rag_qa_context: QueryContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)
        self.es_engine = ESEgine()
        self.mv_engine = MilvusEngine()
        
    @trace_new(op="get_query_recommend", logic_ep=True)
    def get_query_recommend(self):
        try:
            assert self.context.get_question() is not None and len(self.context.get_question()) != 0, self.clogger.info("question为空")

            beginning_time = time.time()

            # 获取必传入参
            question = self.context.get_question()
            return_all = self.context.get_return()
            scheme_id = QueryReConfig["WHITE_LIST_CONFIG"]["query_recommend"]
            input_info = {"query": question}
            results = None
            results = search_whitelist(scheme_id=scheme_id, input_info=input_info)
            if results:
                self.context.set_recommend_query(recommend_query=results[0]["output"]["results"])
            else:
                recall_results = get_recall_results(data={"query": question}, 
                                es_engine=self.es_engine,
                                mv_engine=self.mv_engine,
                                use_channel=QueryReConfig["QUERYRECDB"]["Recall"]["use_channel"],
                                search_type=QueryReConfig["QUERYRECDB"]["Recall"]["search_type"],
                                index_name= QueryReConfig["QUERYRECDB"]["ES"]["index_name"],
                                collection_name=QueryReConfig["QUERYRECDB"]["MV"]["collection_name"],
                                )
                if return_all:
                    rank_results = get_ranking_reuslts(data=recall_results,query=question, return_all=return_all,**QueryReConfig["QUERYRECDB"]["Ranking"])
                    recommend_ = []
                    for questions in rank_results:
                        questions[1]["query"] = questions[0]
                        recommend_.append(questions[1])
                    self.context.set_recommend_query(recommend_query=recommend_)
                else:
                    rank_results = get_ranking_reuslts(data=recall_results,query=question,return_all=return_all,**QueryReConfig["QUERYRECDB"]["Ranking"])
                    recommend_questions = [questions[0] for questions in rank_results]
                    self.context.set_recommend_query(recommend_query=recommend_questions)
                # initialize return info
            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ''

            self.clogger.info(
                "get_query_recommend success, use time {}s".format(round(time.time() - beginning_time, 2)))
        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.QUERY_RECOMMEND_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)

        return {"is_success": is_success,
                "return_code": return_code,
                "detail": error_detail,
                "timestamp": str(time.time()),
                "err_msg": err_msg
                }
    

if __name__ == "__main__":
    test_question_list = ["2024年上海人工智能", "人工",
                          "上海", "无神论者是否不尊重其他文化？", "习近平",
                          "列举山西省农业农村厅制定的技术支撑文件中包含的主要内容。"]
    for i in range(len(test_question_list)):
        session_idx = "mock_session_{}".format(i)
        context = QueryContext(request_id=get_md5(session_idx))
        context.set_question(test_question_list[i])
        context.set_return(True)
        response = QueryRecommendTask(context).get_query_recommend()
        print(test_question_list[i], response)
        print("context.get_recommend_query:{}".format(context.get_recommend_query()))