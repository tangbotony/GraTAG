import sys
import time
import json
import traceback
from include.utils import ArcNode
from include.logger import ContextLogger
from include.context import RagQAContext, RagQAReturnCode
from include.utils import pool_async
from modules.query_judge_group.judge_func_rag_stepback import judge_process
from include.decorator import timer_decorator


class QueryJudgeTask:
    """ 问题属性判定
    """
    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.dag = self.context.get_dag()   # 默认取general_dag
        self.log = ContextLogger(self.context)
        self.log.info("callQueryJudge")
        
    @timer_decorator
    def get_judge(self, **kwargs):
        try:
            beginning_time = time.time()
            query_list = []
            for i in range(2, len(self.dag.arcnodes)):  # 前两个是start和end节点，所以从2开始
                node = self.dag.arcnodes[i]
                query_list.append(node.val)
            ##### 如果没有以下三个判断需求，则直接返回结果
            check_func_call = kwargs.get("check_func_call", False)
            check_step_back = kwargs.get("check_step_back", False)
            check_need_rag = kwargs.get("check_need_rag", False)
            if not check_func_call and not check_step_back and not check_need_rag:
                judge_final_list = []
                for query in query_list:
                    fake_judge_res = {'query_info': {'type': 'ori_query', 'query': query, 'FunctionCall': None, 'need_rag': True}, 'stepback_info': None}
                    judge_final_list.append(fake_judge_res)
            else:
                judge_final_list = pool_async(judge_process, query_list, log =self.log, **kwargs)

            ## 补充Dag图信息
            for i in range(2, len(self.dag.arcnodes)):  
                node = self.dag.arcnodes[i]
                judge_res = judge_final_list[i-2]
                query_json, stepback_query_json = judge_res["query_info"], judge_res["stepback_info"]

                self.dag.arcnodes[i].FunctionCall = query_json["FunctionCall"]
                self.dag.arcnodes[i].need_rag = query_json["need_rag"]
                # 针对回退新节点，插入到原节点前面
                if stepback_query_json:
                    new_node = ArcNode(stepback_query_json["query"]) 
                    new_node.FunctionCall = stepback_query_json["FunctionCall"]
                    new_node.need_rag = stepback_query_json["need_rag"]
                    self.dag.insert_node_front(new_node, node.val)
                
            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ""
            self.log.info("query_judge success, use time {}s".format(round(time.time() - beginning_time, 2)))
        except Exception as e:
                self.log.error(traceback.format_exc())
                is_success = False
                return_code = RagQAReturnCode.UNKNOWN_ERROR
                error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
                err_msg = str(e)

        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)
