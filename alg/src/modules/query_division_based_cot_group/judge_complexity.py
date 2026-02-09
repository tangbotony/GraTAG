from datetime import datetime
from string import Template
from typing import List
import json
import traceback
import copy
from collections import OrderedDict
from include.config import ModuleConfig
from include.logger import ContextLogger
from include.context import RagQAContext
from include.utils import llm_call, is_digit
from include.utils.multiprocess_utils import pool_async
from include.utils.similarity_utils import get_similarity
from include.utils.post_processer import postprocess_timeline_split
from include.utils.call_white_list import search_whitelist, create_whitelist
from include.utils.post_processer import clean_and_eval, postprocess_multisplit_queries
from include.decorator import timer_decorator



class TimeLineSplitQueries:
    def __init__(self, context:RagQAContext, split_num_threshold:int = 10, max_try:int = 3, **kwargs):
        self.context = context
        self.log = ContextLogger(self.context)
        self.log.info("callQueryDivision-TimeLineSplitQueries")
        self.rewrite_question = copy.deepcopy(self.context.get_question())
        self.split_num_threshold = split_num_threshold
        self.max_try = max_try
        self.model_name = ModuleConfig.timeline_cot_model_name
        self.former_dialogue = get_former_dialogue_queries(self.context, current_query = self.context.get_question())

    def get_timeline_multiqueries(self):
        if ModuleConfig.followup_question and self.former_dialogue:
            return self.get_multi_dialogue_timeline_queries()
        else:
            return self.get_single_dialogue_timeline_queries()
        
    def get_single_dialogue_timeline_queries(self):
        """
        对问题做时间脉络拆分，发出提问
        Args:
            输入：
                question: 问题内容
                max_try: 尝试拆分次数
            输出：
            {
                'is_complex': True,
                'sub_questions': [
                    '2023年中国粮食产量是多少？',
                    '2017年中国粮食产量是多少？',
                    '比较2023年与2017年中国粮食产量的差额'
                ]
            }
        """
        # 时间脉络拆分
        query_dic = {"original_query": self.rewrite_question}
        if self.split_num_threshold != None:
            if self.split_num_threshold < 2:
                self.log.warning(f"拆分个数split_num_threshold设置不可低于 2 ，当前 split_num_threshold 重置为 2。")
                self.split_num_threshold = 2
            query_dic.update({"split_num_threshold": str(self.split_num_threshold)})
            MultiTimelineTemplate = ModuleConfig["MultiTimelineNumThresholdTemplate"]
        else:
            MultiTimelineTemplate = ModuleConfig["MultiTimelineTemplate"]
        prompt = Template(MultiTimelineTemplate).substitute(query_dic)

        response = None
        split_results = None
        try_num = 0
        error_info = None
        while  try_num < self.max_try:
            try:
                response = llm_call(
                        query=prompt,
                        model_name=self.model_name,  
                        temperature = 0.0,      # 时间线拆分的temperature设置为0
                        n=1,
                        max_tokens = 2048
                        )
                response = response.split("\n")
                response = postprocess_multisplit_queries(response)
                split_results = response
                break
            except Exception as e:
                try_num += 1
                error_info = traceback.format_exc()
                pass
        sub_questions = []
        for obj in split_results:
            if obj:
                try:
                    if "." in obj and is_digit(obj[0]):
                        obj = obj.split(".")[1].lstrip().rstrip()
                    else:
                        obj = obj.lstrip().rstrip()
                except:
                    pass 
                sub_questions.append(obj)

        res_dict =  {'is_complex': False,'sub_questions': []}
        if sub_questions != []:
            sub_questions = postprocess_timeline_split(sub_questions)
            # 采用新72B0720版本的SFT模型后，可以不做子问题重写
            # sub_questions = replenish_query_info(self.rewrite_question, sub_questions, self.log)
            res_dict["is_complex"] = True
            res_dict["sub_questions"] = sub_questions

            return res_dict
        else:
            self.log.error(f"Function get_timeline_multiqueries failed. Query:{self.rewrite_question}, LLM_return:{response}.error_info:{error_info}")
            raise ValueError(f"Function get_timeline_multiqueries failed. Query:{self.rewrite_question}, LLM_return:{response}.error_info:{error_info}")

    def get_multi_dialogue_timeline_queries(self):
        """
        对问题做时间脉络拆分，发出提问
        Args:
            输入：
                question: 问题内容
                max_try: 尝试拆分次数
            输出：
            {
                'is_complex': True,
                'sub_questions': [
                    '2023年中国粮食产量是多少？',
                    '2017年中国粮食产量是多少？',
                    '比较2023年与2017年中国粮食产量的差额'
                ]
            }
        """
        query_dic = {
            "former_dialogue": self.former_dialogue,
            "original_query": self.rewrite_question
            }  
        QueryDependencyTemplate = ModuleConfig["QueryDependencyTemplate"]
        prompt = Template(QueryDependencyTemplate).substitute(query_dic)
        former_relation = None
        try_num = 0
        while  try_num < self.max_try:
            try:
                response = llm_call(
                        query=prompt,
                        model_name=self.model_name,  
                        temperature = 0.0,   # 问题依赖关系的temperature设置为0
                        n=1,
                        max_tokens = 2048
                        )
                
                if type(response) == list:
                    response = clean_and_eval(response[0])
                else:
                    response = clean_and_eval(response)
                assert (type(response) == dict and "former_topic_related" in response and "rewrited_question" in response)
                former_relation = response
                break
            except Exception as e:
                try_num += 1
                former_relation = {'former_topic_related':True, 'rewrited_question':f'{self.former_dialogue} {self.rewrite_question}'}
                pass
        if former_relation["former_topic_related"] and former_relation["rewrited_question"] and "None" not in former_relation["rewrited_question"]:
            self.rewrite_question = former_relation["rewrited_question"]
            self.log.info(f"基于多轮对话历史对query改写成功，历史话题{self.former_dialogue}, 原query{self.rewrite_question}，改写后{self.rewrite_question}")

        return self.get_single_dialogue_timeline_queries()



class MultiHopSplitQueries:
    def __init__(self, context:RagQAContext, split_num_threshold:int = 3, max_try:int = 3, **kwargs):
        self.context = context
        self.log = ContextLogger(self.context)
        self.log.info("callQueryDivision-MultiHopSplitQueries")
        self.rewrite_question = self.context.get_question()
        self.rewirte_appendix_info = self.context.get_rewrite_appendix_info()
        self.split_num_threshold = split_num_threshold
        self.max_try = max_try
        self.sft_model_name = ModuleConfig.general_cot_model_name
        self.large_model_name = ModuleConfig.large_model_name
        self.former_dialogue = get_former_dialogue_queries(self.context, current_query = self.rewrite_question)

    def get_multi_hop_queries(self):
        """
        对问题做分析，判定是否是复杂问题，并对复杂问题拆分成子问题，并判定子问题是否需要外界信息输入调用RAG
        可以处理单轮对话和多轮对话的问题拆分。        
        Args:
            输入：
                question: 问题内容
                appendix_info: 补充的信息，字符列表形式
                max_try: 尝试拆分次数
            输出：
            {
                'is_complex': True,
                'sub_questions': [
                    '2023年中国粮食产量是多少？',
                    '2017年中国粮食产量是多少？',
                    '比较2023年与2017年中国粮食产量的差额'
                ]
            }
        """
        if ModuleConfig.followup_question and self.former_dialogue:
            return self.get_dialogue_multihop_queries()
        else:
            return self.get_single_multihop_queries()


    def get_single_multihop_queries(self):
        """
        单轮对话问题拆分
        """
        query_dic = {"original_query": self.rewrite_question}
        if self.rewirte_appendix_info and self.rewirte_appendix_info["is_supply"] and len(self.rewirte_appendix_info["supply_info"]) > 0:   
            # 信息补充条件下的拆分    
            recall_num = 1      
            query_dic.update({"supply_info": "、".join(self.rewirte_appendix_info["supply_info"])})
            MultiSplitSupplyTemplate = ModuleConfig["MultiSplitSupplyTemplate"]
            prompt = Template(MultiSplitSupplyTemplate).substitute(query_dic)
        elif isinstance(self.split_num_threshold, int):     
            # 通用问题拆分 限制子问题条数      
            recall_num = 1     # 由于temperature 设置为0.1所以这里只返回一个llm输出。
            if self.split_num_threshold < 2:
                self.log.warning(f"拆分个数split_num_threshold设置不可低于 2 ，当前 split_num_threshold 重置为 2。")
                self.split_num_threshold = 2
            query_dic.update({"split_num_threshold": str(self.split_num_threshold)})
            MultiHopQueryNumThresholdTemplate = ModuleConfig["MultiHopQueryNumThresholdTemplate"]
            prompt = Template(MultiHopQueryNumThresholdTemplate).substitute(query_dic)
        else:
            # 通用问题拆分      
            recall_num = 1       
            MultiHopQueryTemplate = ModuleConfig["MultiHopQueryTemplate"]
            prompt = Template(MultiHopQueryTemplate).substitute(query_dic)

        try_num = 0
        response = None
        res_dict = {'is_complex': False,'sub_questions': []}
        while  try_num < self.max_try:
            try:
                response = llm_call(
                        query=prompt,
                        model_name=self.sft_model_name,  
                        n=recall_num,             
                        temperature=0.0,        # 通用拆分的temperature设置为0.0
                        session_id=self.context.get_session_id()
                        )
                if type(response) == list:
                    if self.split_num_threshold:
                        response = select_numsplit_response(response, self.split_num_threshold)
                    else:
                        response = clean_and_eval(response[0])
                else:
                    response = clean_and_eval(response)

                assert type(response) == dict and "is_complex" in response and  "sub_questions" in response
                if response["is_complex"] == True or response["is_complex"] in ("True", "true"):
                    assert len(response["sub_questions"]) >= 1
                    assert all([isinstance(obj, str) for obj in response["sub_questions"]])
                    if get_similarity([response["sub_questions"][0]], [self.rewrite_question])[0][0] > 0.95:
                        response = {'is_complex': False, 'sub_questions': []}
                res_dict = response
                break
            except Exception as e:
                try_num += 1
                # log.error(f"COT拆分模型返回错误，返回的response有{response}。报错：{str(traceback.format_exc())}")
                pass
        if not res_dict:
            self.log.error(f"调用 COT general 失败了哈 Query:{self.rewrite_question}, LLM_return:{response}")
        else:
            self.log.info(f"调用 COT general {self.sft_model_name} 拆分结果为{res_dict}")
        if res_dict["is_complex"]:
            post_split_queries = postprocess_multisplit_queries(res_dict["sub_questions"])
            similar_queries = get_filtered_queries(self.rewrite_question, post_split_queries, clip_low =0.25)
            # 采用新72B0720版本的SFT模型后，可以不做子问题重写
            # rewrited_queries = replenish_query_info(self.rewrite_question, similar_queries, self.log)
            res_dict = {'is_complex': post_split_queries != [], 'sub_questions': similar_queries}

        return res_dict


    def get_dialogue_multihop_queries(self):
        """
        多轮对话问题拆分
        """
        
        recall_num = 1     # 由于temperature 设置为0.1所以这里只返回一个llm输出。
        if self.split_num_threshold < 2:
            self.log.warning(f"拆分个数split_num_threshold设置不可低于 2 ，当前 split_num_threshold 重置为 2。")
            self.split_num_threshold = 2
        query_dic = {
            "former_dialogue": self.former_dialogue,
            "original_query": self.rewrite_question,
            "split_num_threshold": str(self.split_num_threshold),
            }  
        MultiHopQueryDialogueNumThresholdTemplate = ModuleConfig["MultiHopQueryDialogueNumThresholdTemplate"]
        prompt = Template(MultiHopQueryDialogueNumThresholdTemplate).substitute(query_dic)

        try_num = 0
        response = None
        res_dict = {'former_topic_related':False, 'is_complex': False, 'sub_questions': []}
        while try_num < self.max_try:
            try:
                response = llm_call(
                        query=prompt,
                        model_name=self.large_model_name,  
                        n=recall_num,             
                        temperature = 0.0       # 通用拆分的temperature设置为0.1
                        )
                if type(response) == list:
                    if self.split_num_threshold:
                        response = select_numsplit_response(response, self.split_num_threshold)
                    else:
                        response = clean_and_eval(response[0])
                else:
                    response = clean_and_eval(response)

                assert type(response) == dict and "is_complex" in response and  "sub_questions" in response
                if response["is_complex"] == True or response["is_complex"] in ("True", "true"):
                    assert len(response["sub_questions"]) >= 1
                    assert all([isinstance(obj, str) for obj in response["sub_questions"]])
                res_dict = response
                break
            except Exception as e:
                try_num += 1
                # log.error(f"COT拆分模型返回错误，返回的response有{response}。报错：{str(traceback.format_exc())}")
                pass
            
        if not res_dict:
            self.log.error(f"调用 COT general 失败了哈 Query:{self.rewrite_question}, LLM_return:{response}")
        else:
            self.log.info(f"调用 COT general {self.large_model_name} 拆分结果为{res_dict}")
        
        # 子问题主体信息补充 + 相似度过滤
        if res_dict["former_topic_related"]:
            dialogue = f"{self.former_dialogue} {self.rewrite_question}"
            self.log.info(f"模型判定历史会话主题与当前问题有关系，历史主题：{self.former_dialogue} 当前问题：{self.rewrite_question}")
        else:
            dialogue = self.rewrite_question
            self.log.info(f"模型判定历史会话主题与当前问题无关，历史主题：{self.former_dialogue} 当前问题：{self.rewrite_question}")

        if res_dict["is_complex"]:
            # 复杂问题：子问题后处理 + 相似度过滤
            post_split_queries = postprocess_multisplit_queries(res_dict["sub_questions"])
            similar_queries = get_filtered_queries(self.rewrite_question, post_split_queries, clip_low =0.25, clip_high=0.95)
            # 采用新72B0720版本的SFT模型后，可以不做子问题重写
            # rewrited_queries = replenish_query_info(dialogue, similar_queries, self.log)
            res_dict = {'is_complex': post_split_queries != [], 'sub_questions': similar_queries}
        else:
            # 是简单问题但与前文相关：原问题重写，重写后原问题做context覆盖
            if res_dict["former_topic_related"]:
                rewrited_question_tmp = replenish_query_info(self.former_dialogue, [self.rewrite_question], self.log)
                if rewrited_question_tmp != []:
                    self.context.set_question(rewrited_question_tmp[0])

        return res_dict

# 对重写的问题做过滤
def get_filtered_queries(ori_query, rewrited_queries, clip_high = None, clip_low = None):
    assert any([isinstance(clip_high, float), isinstance(clip_low, float)])
    similarity_matrix = get_similarity([ori_query], rewrited_queries)[0]
    if clip_low and not clip_high:
        filtered_rewrited_queries = [rewrited_queries[i] for i in range(len(similarity_matrix)) if similarity_matrix[i] > clip_low]
    if clip_high and not clip_low:
        filtered_rewrited_queries = [rewrited_queries[i] for i in range(len(similarity_matrix)) if similarity_matrix[i] < clip_high]
    if clip_low and clip_high:
        filtered_rewrited_queries = [rewrited_queries[i] for i in range(len(similarity_matrix)) if clip_low < similarity_matrix[i] < clip_high]
    return filtered_rewrited_queries
    

def replenish_query_info(question:str, queries: List[str], log:ContextLogger, max_try: int = 3, model_name:str = ModuleConfig.light_model_name):
    """
    根据原问题中的时间地点人物信息对拆分后的子问题做重写
    Args:
        输入： 原问题 question， 子问题列表 queries
        输出： 重写后的子问题列表   
    """

    ReplenishQueryInfoTemplate = ModuleConfig["ReplenishQueryInfoTemplate"]

    def replenish_text(query:str):
        query_dic = {"original_query": question, "split_query":query}
        prompt = Template(ReplenishQueryInfoTemplate).substitute(query_dic)
        replenish_query = query
        response = None
        try_num = 0
        while  try_num < max_try:
            try:
                response = llm_call(
                        query=prompt,
                        model_name=model_name,  
                        add_template = True, 
                        temperature = 0.0,
                        n=1,
                        max_tokens = 50
                        )
                post_response = postprocess_multisplit_queries([response])
                assert post_response != []
                response = post_response[0]
                if "不用转写" not in str(response):
                    replenish_query = response
                    log.info(f"子问题重写成功 原query:{query}，新query:{replenish_query}")
                break
            except:
                try_num += 1
                pass
        return replenish_query
    replenish_queries = pool_async(replenish_text, queries,)
    low_thred = 0.6
    if len(question) // (sum([len(replenish_query) for replenish_query in replenish_queries])//len(replenish_queries)) > 3:
        low_thred = 0.4   # 针对长度差距过大的句子相似度应该适当放松
    replenish_queries_filtered = get_filtered_queries(question, replenish_queries, clip_low=low_thred, clip_high=0.98)
    if len(replenish_queries_filtered) < len(replenish_queries):
        log.info(f"子问题重写后与其他子问题信息出现重复，原sub_queries {str(replenish_queries)}, 去重后 {str(replenish_queries_filtered)}")
    return replenish_queries_filtered
    

def get_former_dialogue_queries(context, current_query = ""):
    """
    仅查询抽取倒数的三个问题，作为历史对话内容
    """
    former_queries = context.get_history_questions(del_current_query = True)
    if former_queries != []:
        extract_former_queries = former_queries[-3:]                                   # 取倒数三个query
        extract_former_queries = list(OrderedDict.fromkeys(extract_former_queries))    # 去重
        # if current_query:                                                            # 过滤掉相似度低的历史问题，误杀太多了，先不启用
        #     extract_former_queries = get_filtered_queries(current_query, extract_former_queries, clip_low=0.5, clip_high=0.98)
        return " | ".join(extract_former_queries)
    else:
        return ""
    
# 过滤拆分子问题个数小于等于 split_num_threshold 个的结果
def select_numsplit_response(response, split_num_threshold):
    response = sorted(response, key=lambda x:len(x), reverse=True)
    for obj in response:
        try:
            obj = clean_and_eval(obj)
            if obj["is_complex"] == False:
                return obj 
            if len(obj["sub_questions"]) <= split_num_threshold:
                return obj
        except:
            pass
    return None

def check_dependency_map(questions: List, log:ContextLogger):
    """
    判定一串问题中每两个子问题之间是否有依赖关系
    Args:
        questions: 问题串，顺序要注意是从逻辑头到逻辑尾，如果翻转则测不准确。[query1, query2, query3...]
    Output:
        group: 记录每个node依赖上游的id，[[], [], [], [0, 2]]
    """
    questions_pairs = []
    idx_records = []
    for i in range(1, len(questions)):
        for j in range(0, i):
            questions_pairs.append([questions[i], questions[j]])  # [[ques, former1], [ques, former2]...]
            idx_records.append([i, j])
    judge_res = pool_async(check_dependency, questions_pairs, log = log)
    judge_record = [obj if isinstance(obj, bool) else False for obj in judge_res]

    group = [[] for _ in range(len(questions))]
    for related, pairs_id in zip(judge_record, idx_records):
        if related:
            group[pairs_id[0]].append(pairs_id[1])  

    return group


def check_dependency(queries_input: List, log:ContextLogger = None, max_try:int = 3, model_name:str = ModuleConfig.light_model_name):
    """
    判定两个子问题之间是否有依赖关系
    Args:
        queries_input 输入的判定问题，注意顺序 [cur_query, former_query]
    Output:
        True/False
    """
    QueryDependencyTemplate = ModuleConfig["QueryDependencyTemplate"]
    query_dic = {
        "original_query": queries_input[0],
        "former_query": queries_input[1]
    }
    prompt = Template(QueryDependencyTemplate).substitute(query_dic)

    try_num = 0
    while try_num < max_try:
        try:
            response = llm_call(
                    query=prompt,
                    model_name=model_name,
                    temperature = 0.0,
                    n=1,
                    max_tokens = 10
                    )   
            if type(response) == list and len(response) == 1:
                response = eval(response[0])
            else:
                response = eval(response)
            res = response
            break
        except:
            try_num += 1
            pass

    if res == None:
        log.error(f"非独立问题的判定没有正常返回，LLM返回为：{response}")
        raise Exception("Check dependency question failed.")
    
    if isinstance(res, bool):
        return res
    else:
        return "True" in res



if __name__ == "__main__":
    import time
    st = time.time()
    # test1
    # appendix_info = {"is_supply": False, "supply_info":  ["言能力的提升", "对中文文化的理解", "职业生涯的影响", "个人生活的改变"]}
    # res = get_multi_hop_queries("学习倒立对人的影响有哪些？", appendix_info=appendix_info)
    # # res = get_timeline_multiqueries("学习倒立对人的影响有哪些？")
    # print(res, time.time() - st)
    # exit()


    # res = check_time_location("根据1月1日上海的天气情况，应该穿什么样的衣服？")
    # print(res, time.time() - st)
    # exit()

    # ques_list =["上海有哪些新开的公园？", "这些公园需要门票吗？", "老人可以免票进入这些公园吗"]
    # res = check_dependency_map(ques_list, None)
    # print(res)
    # exit()


    res = check_dependency(["山西省的古代建筑包括辽代吗", "山西省的古代建筑有哪些？"])
    print(res)