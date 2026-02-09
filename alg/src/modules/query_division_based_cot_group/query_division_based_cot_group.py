import traceback
import json
import time
import requests
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.context import RagQAContext, RagQAReturnCode
from include.logger import ContextLogger
from include.utils import ArcNode, IGraph
from modules.query_judge_group import QueryJudgeTask
from include.utils.Igraph_utils import construct_dag
from include.decorator import timer_decorator
from modules.query_division_based_cot_group.rewrite_query import TimeLocRewrite
from modules.query_division_based_cot_group.judge_complexity import MultiHopSplitQueries, TimeLineSplitQueries, check_dependency_map

class QueryDivisionBasedCoTTask:
    """ 问题重写、扩写 task, 问题增强模块自行定义，可放在这里，也可单独定义 task
    """
    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.log = ContextLogger(self.context)
        self.log.info("callQueryDivision")
        self.query = self.context.get_question()              # 用户输入的query
        self.basic_info = self.context.get_basic_user_info()  # 用户的IP信息
        self.appendix_info = self.context.get_supply_info()   # 用户输入的补充信息
        assert isinstance(self.query, str) and self.query != "", "用户输入的query为空"
        assert self.basic_info["User_Date"] != "", "用户的时间信息为空"
        assert self.basic_info["User_IP"] != "", "用户的IP信息为空"

    @timer_decorator
    def get_cot(self, use_scene:str = "general", **kwargs):
        """
        Args:
            parallel:bool  设定是否并行COT，默认False串行
            new_query:str  Timeline需求，输入的重写query
            use_scene:str  使用场景 general 或 timeline
            split_num_threshold: int   COT拆分子问题个数
        """
        try:
            beginning_time = time.time()
            if kwargs.get("pro_flag", True):
                if use_scene == "general":
                    self.query_rewrite_general(**kwargs)
                    cot_ans = self.context.get_dag().get_turns()[1]
                else:
                    self.query_rewrite_timeline(**kwargs)
                    cot_ans = self.context.get_timeline_dag().get_turns()[1]
                # 发送飞书信息
                used_time = time.time() - beginning_time
            else:
                dag = construct_dag([self.context.get_question()])
                dag.origin_query = self.context.get_origin_question()
                dag.rewrite_query = self.context.get_question()
                self.context.set_dag(dag)

            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ""
            self.log.info(
                "query_division success, use time {}s".format(round(time.time() - beginning_time, 2)))
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
    
    
    def query_rewrite_general(self, if_parallel:bool = False, **kwargs):
        """
        Introduction:前处理 preprocess_time_Loc 提取并过滤掉单个的时间地点信息，
                     问题重写 rewrite_add_timeloc 对query做时间地点补写
                     复杂问题拆分 get_multi_hop_queries 基于 appendix_info(若非空) 做多角度拆分
                     子问题依赖关系检查 check_dependency_map 多线程进行
                     构建有向无环图 IGraph
                     调用 QueryJudgeTask 模块 更新每个节点的query属性
        """
        # STEP 1  问题思维链拆分
        rewrite_query = self.context.get_question()
        multihop_dict = MultiHopSplitQueries(self.context, **kwargs).get_multi_hop_queries()
        # STEP 2 dag构建
        if multihop_dict["is_complex"]:
            sub_questions = multihop_dict["sub_questions"]
            if len(rewrite_query) > 100:   # 过长的问题拆分不一定准确，添加原问题用于检索。
                sub_questions.append(rewrite_query)
            if if_parallel:
                dag = construct_dag(sub_questions)
            else:
                related_records = check_dependency_map(sub_questions, self.log)
                dag = construct_dag(sub_questions, related_records=related_records)
        else:
            dag = construct_dag([rewrite_query])
        dag.origin_query = self.context.get_origin_question()
        dag.rewrite_query = rewrite_query
        self.context.set_dag(dag)

        # STEP 4 调用判定模块，对关系图的属性做重写，输入check** 置为True表示启用对应的属性判断。
        QueryJudgeTask(self.context).get_judge(check_func_call = False, check_step_back = False, check_need_rag = False)
        return 
    
    def query_rewrite_timeline(self, **kwargs):
        """
        Introduction: 对query做时间线拆分 get_timeline_multiqueries
                      构建图 IGraph 每个节点默认需要检索
        """
        # STEP 1 思维链拆分
        input_query = self.query
        multihop_dict = TimeLineSplitQueries(self.context, **kwargs).get_timeline_multiqueries()

        # STEP 2 dag构建
        dag = IGraph()
        if multihop_dict and multihop_dict["is_complex"]:  
            sub_questions = multihop_dict["sub_questions"]
            sub_questions.insert(0, input_query) # 原问题插入到第一个位置，一起检索
            for i, ques in enumerate(sub_questions):
                node = ArcNode(ques) 
                node.need_rag = True     # 时间线脉络场景默认全需要检索
                dag.add_new_node(node)
        else:
            node = ArcNode(input_query) 
            node.need_rag = True
            dag.add_new_node(node)
        dag.origin_query = self.context.get_origin_question()
        dag.rewrite_query = input_query
        self.context.set_timeline_dag(dag)
        return




if __name__ == "__main__":
    from include.utils.text_utils import get_md5

    # lis = ["昆山龙哥事件具体是怎样的", "受害者是谁", "有什么相关法律？", "美国301政策细则", "相关政策还有哪些", "我国外贸受到什么影响", "欧盟最新对华新能源汽车政策", "新能源汽车在欧洲的销售情况", "我国房地产新政"]
    # while True:
    #     query = "张建明在加入上海仪电（集团）有限公司后，带来了哪些新的管理理念或策略？"
    #     context = RagQAContext(session_id=get_md5(query))
    #     context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
    #     context.set_supply_info({"is_supply":False, "supply_info":["北京"]})
    #     context.set_basic_user_info({"User_Date":time.time(), "User_IP":'39.99.228.188'})
    #     TimeLocRewrite(context).rewrite_query_with_supplyment()
    #     QueryDivisionBasedCoTTask(context).get_cot(use_scene="general",split_num_threshold = 6, if_parallel = True)
    #     # print("ori", context.get_origin_question())
    #     # print("now", context.get_question())
    #     _, res, _ = context.get_dag().get_turns()
    #     for obj in res:
    #         print("答案是1：", obj)
    #     # QueryDivisionBasedCoTTask(context).get_cot(use_scene="timeline", split_num_threshold = 5)
    #     # _, res2, _ = context.get_timeline_dag().get_turns()
    #     # for obj in res2:
    #     #     print("答案是2：", obj)
    #     break

    # exit()

    lis = ["河南老人的儿子去世，车子不见了，荣威，发动全城帮忙找车的事情你知道吗，帮我搜索一下新闻", '针对这件事情，写一篇500字左右的评论']
    time_ = 0
    while time_ < 1:
        time_ += 1
        query = ""
        context = RagQAContext(session_id=get_md5("多轮对话"))
        query = lis[0]
        context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
        query = lis[1]
        # context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
        # query = lis[2]
        context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
        context.set_supply_info({"is_supply":False, "supply_info":["北京"]})
        context.set_basic_user_info({"User_Date":time.time(), "User_IP":'39.99.228.188'})
        # TimeLocRewrite(context).rewrite_query_with_supplyment()
        # print("时间改写后问题：", context.get_question())

        QueryDivisionBasedCoTTask(context).get_cot(use_scene="general",split_num_threshold = 6, if_parallel = True)
        _, res, _ = context.get_dag().get_turns()
        for obj in res:
            print("答案是1：", obj)

        # QueryDivisionBasedCoTTask(context).get_cot(use_scene="timeline", split_num_threshold = 5)
        # _, res, _ = context.get_timeline_dag().get_turns()
        # for obj in res:
        #     print("答案是2：", obj)
    exit()