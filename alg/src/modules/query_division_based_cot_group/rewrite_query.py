import json
import time
import copy
import traceback
from string import Template
from typing import List
from concurrent.futures import ThreadPoolExecutor,as_completed
import re
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.config import ModuleConfig
from include.logger import ContextLogger
from include.context import RagQAContext, RagQAReturnCode, DocQAContext
from include.utils.abstract_utils import news_retrieval_summary
from include.utils.llm_caller_utils import llm_call
from include.utils.parse_time_loc import parse_time_location, parse_web_date, filter_web_summary_with_date
from include.utils import edit_distance, get_date_info
from include.decorator import timer_decorator

REPLACE_WORD_MAP = {
    "表格": "汇总信息",
    "代码": "解决办法"
    }


class TimeLocRewrite:
    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.log = ContextLogger(self.context)
        self.log.info("callTimeLocRewrite")
        self.query = self.context.get_question()              # 用户输入的query
        self.basic_info = self.context.get_basic_user_info()  # 用户的IP信息
        self.appendix_info = self.context.get_supply_info()   # 用户输入的补充信息
        self.context.set_rewrite_appendix_info(self.context.get_supply_info())  # 初始化
        self.rewrite_appendix_info = copy.deepcopy(self.appendix_info)
        assert isinstance(self.query, str) and self.query != "", "用户输入的query为空"
        assert self.basic_info["User_Date"] != "", "用户的时间信息为空"
        assert self.basic_info["User_IP"] != "", "用户的IP信息为空"


    @timer_decorator
    def rewrite_query_with_supplyment(self):
        """
        根据query和supplyment中对时间和地点的描述，做抽取、重写、回填到query的操作
        example：本地今天的新闻有什么  supply_info:上海  
                ->>  2024年6月24日上海的新闻有什么 
        """
        try:
            beginning_time = time.time()
            # 获取用户的日期 & 补充地点
            basic_info = parse_time_location(self.basic_info) 
            user_date = basic_info["User_Date"]
            added_loc = self.extract_loc_info(self.appendix_info)
            # 相对时间改写
            time_rewrite_query = self.rewrite_add_time(self.query, user_date)
            if time_rewrite_query != self.query:
                self.log.info(f"时间重写&嵌入模块运行成功, 原问题 '{self.query}' 改写后 '{time_rewrite_query}'")
            # 对地点添加改写
            loc_rewrite_query = self.rewrite_add_loc(time_rewrite_query, added_loc)
            if loc_rewrite_query != time_rewrite_query:
                self.log.info(f"地点重写模块运行成功, 原问题 '{time_rewrite_query}' 改写后 '{loc_rewrite_query}'")
            rewrite_query = loc_rewrite_query
            # 关键词语替换
            filtered_rewrite_query = self.replace_one_word(rewrite_query)
            if filtered_rewrite_query != rewrite_query:
                rewrite_query = filtered_rewrite_query
                self.log.info(f"关键词过滤替换成功, 原问题 '{rewrite_query}' 替换后 '{filtered_rewrite_query}'")
            # 新query对原query做覆盖
            if rewrite_query != self.query:
                self.context.set_origin_question(self.context.get_question())
                self.context.set_question(rewrite_query)

            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ""
            self.log.info(
                "query rewrite success, use time {}s".format(round(time.time() - beginning_time, 2)))
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

    def extract_loc_info(self, appendix_info_dic):
        """
        功能：分析用户输入的补充信息词汇，如果只有一个时间地点，就是补充时间地点信息；如果是多个，则为拆分角度。
        Args: 
            输入：['上海', '9月', '3月']
            输出：('', '上海', ['9月', '3月'])
            注意本版本只提取地点信息，不做时间提取
        """
        if appendix_info_dic["is_supply"]:
            supply_lis = appendix_info_dic["supply_info"]
        else:
            return ""
        nlp = ModuleConfig.spacy_nlp
        word_lis = []
        date_word = ""
        pos_word = ""
        # date_lis = []
        loc_lis = []
        for text in supply_lis:
            entity = nlp(text)
            if len(entity.ents) != 1:
                word_lis.append(text)
                continue
            ent = entity.ents[0]
            # if ent.label_ == "DATE":
            #     date_lis.append(text)
            #     date_word = text
            if ent.label_ in ["LOC"]:   
                loc_lis.append(text)
                pos_word = text 
            elif ent.label_ in ["GPE"] and text in ModuleConfig.city_names: 
                loc_lis.append(text)
                pos_word = text 
            else:
                word_lis.append(text)
        # if len(date_lis) > 1:
        #     word_lis += date_lis
        #     date_word = ""
        if len(loc_lis) > 1:
            word_lis += loc_lis
            pos_word = ""
        # 补充信息如果提取了地点，则需要更新补充列表
        if pos_word:
            appedix_info = {"is_supply":appendix_info_dic["is_supply"], "supply_info":word_lis}
            self.context.set_rewrite_appendix_info(appedix_info)
        return pos_word

    def replace_one_word(self, query):
        simi_query = query
        for key_word, replace_word in list(REPLACE_WORD_MAP.items()):
            if key_word in query:
                simi_query = query.replace(key_word, replace_word)
                self.context.set_question(simi_query)
                break 
        return simi_query
    
    def rewrite_add_time(self, query,  user_date, max_try:int = 3, max_tokens:int=256, model_name: str = ModuleConfig.light_model_name):
        TimeRewriteTemplate = ModuleConfig["TimeRewriteTemplate"]
        TimeInsertTemplate = ModuleConfig["TimeInsertTemplate"]
        query_dic = {"original_query": query, "date":user_date}
        rewrite_prompt = Template(TimeRewriteTemplate).substitute(query_dic)
        insert_prompt = Template(TimeInsertTemplate).substitute(query_dic)
        prompts = [rewrite_prompt, insert_prompt]

        rewrite_response = None
        @timer_decorator
        def call_llm_rewrite_time(prompts_list):
            responses = ["{'final_answer': '无需改写'}", "{'final_answer': '无需改写'}"]
            try_num = 0
            while try_num < max_try:
                try:
                    responses = llm_call(query=prompts_list, is_parallel = True, model_name=model_name, max_tokens=max_tokens,
                                        temperature=0.0, n=1, session_id=self.context.get_session_id())
                    assert "final_answer" in responses[0] and "final_answer" in responses[1]
                    break
                except:
                    try_num += 1
                    pass
            return responses
        
        if ModuleConfig.use_web_summary_rewrite_query:
            futures = {}
            with ThreadPoolExecutor(max_workers=5) as executor:
                future = executor.submit(call_llm_rewrite_time, prompts)
                futures[future] = 0
                future = executor.submit(news_retrieval_summary, query = query)
                futures[future] = 1
                # 按照提交顺序收集结果
                results = [None] * 2
                for future in as_completed(futures):
                    idx = futures[future]
                    result = future.result()
                    results[idx] = result
                rewrite_response, insert_response = results[0]
                web_summary = results[1]
            # 网页预检索格式删选，没有时间信息的删除
            web_summary = filter_web_summary_with_date(web_summary)
        else:
            rewrite_response, insert_response = call_llm_rewrite_time(prompts)
            web_summary = []

        # 时间重写检验
        if rewrite_response:
            rewrite_query = self.postprocess_rewrite_res(rewrite_response)
            if rewrite_query != "":
                return rewrite_query
        
        # 时间嵌入检验
        if insert_response:
            inserted_query = self.postprocess_insert_res(insert_response, query)
            if inserted_query != "":
                return inserted_query
        
        if ModuleConfig.use_web_summary_rewrite_query == False or len(web_summary) < 1:
            return query
        # 大模型判断为不需要重写，再次通过网页摘要做出判断，如果是近期的热点新闻，则做时间补充（仅两个月内的补充到现在月份，两个月以外的补充到年份）
        news_year, news_month, news_day = parse_web_date([web_summary[i]["publish_time"] for i in range(len(web_summary))])
        now_year, now_month, now_day = get_date_info(self.basic_info["User_Date"])
    
        if news_year == now_year:
            if now_month - news_month < 3:
                fake_insert_response =  "{'final_answer': '月'}"
            else:
                fake_insert_response =  "{'final_answer': '年'}"
            inserted_query = self.postprocess_insert_res(fake_insert_response, query)
            self.log.info(f"{query} 网页摘要时间信息 {news_year, news_month, news_day}")
            return inserted_query
        elif now_year - news_year == 1: # 如果新闻是上一年的，指定到上一年
            fake_insert_response =  "{'final_answer': '年'}"
            inserted_query = self.postprocess_insert_res(fake_insert_response, query, specified_date=[news_year, news_month, news_day])
            self.log.info(f"{query} 网页摘要时间信息 {news_year, news_month, news_day}")
            return inserted_query

        return query

    def rewrite_add_loc(self, query,  added_loc, max_try:int = 3, max_tokens:int=256, model_name: str = ModuleConfig.light_model_name):
        if added_loc == "":
            return query
        Loc_Template = ModuleConfig["Loc_Template"]
        prompt = Loc_Template.format(added_loc, query)
        response = None
        try_num = 0
        while try_num < max_try:
            try:
                response = llm_call(query=prompt, model_name=model_name, max_tokens = max_tokens, temperature = 0.0, n=1)
                response = response[0] if type(response) == list and len(response) == 1 else response
                assert edit_distance(query, response) < len(added_loc) * 2
                break
            except:
                try_num += 1
                pass
        if response:
            return response
        else:
            return query
        
    def postprocess_rewrite_res(self, raw_rewrite):
        answer_slice = raw_rewrite.split("\n")
        answer = "无需改写"
        for line in answer_slice:
            if "final_answer" in line:
                try:
                    answer = eval(line)["final_answer"]
                except:
                    answer = line.split("final_answer")[1].strip(": }'\"")
                    self.log.warning(f"时间重写后处理采用模糊处理，{line} >>提取>> {answer}")
                break
        # 返回不规范&拒绝改写的情况直接返回空字符串
        if "无需改写" in answer:
            return ""
        else:
            return answer
        
    def postprocess_insert_res(self, raw_insert_info, query, specified_date = None):
        answer_slice = raw_insert_info.split("\n")
        answer = "无需改写"
        for line in answer_slice:
            if "final_answer" in line:
                try:
                    answer = eval(line)["final_answer"]
                except:
                    answer = line.split("final_answer")[1].strip(": }'\"")
                    self.log.warning(f"时间嵌入后处理采用模糊处理，{line} >>提取嵌入判断为>> {answer}")
                break
        # 返回不规范&拒绝改写的情况直接返回空字符串
        inserted_query = ""
        if "无需改写" not in answer:
            if specified_date:
                year, month, day = specified_date
            else:
                year, month, day = get_date_info(self.basic_info["User_Date"])
            if answer == "年":
                inserted_query = f"{year}年，" + query
            elif answer == "月":
                inserted_query = f"{year}年{month}月，" + query
            elif answer == "日":
                inserted_query = f"{year}年{month}月{day}日，" + query
            else:
                pass 
        return inserted_query


class TokenNumRewrite:
    def __init__(self, rag_qa_context: DocQAContext):
        self.context = rag_qa_context
        self.log = ContextLogger(self.context)
        self.log.info("callTokenNumRewrite")
        self.query = self.context.get_question()              # 用户输入的query


    @timer_decorator
    def rewrite_token_num_requirement(self):
        """
        根据query和supplyment中对时间和地点的描述，做抽取、重写、回填到query的操作
        example：本地今天的新闻有什么  supply_info:上海  
                ->>  2024年6月24日上海的新闻有什么 
        """
        try:
            beginning_time = time.time()
            TokenNumRewriteTemplate = ModuleConfig["TokenNumRewrite"]
            prompt = TokenNumRewriteTemplate.format(self.query)
            max_try = 3
            response = "<output>无需修改</output>"
            try_num = 0
            while try_num < max_try:
                try:
                    response = llm_call(query=prompt, model_name=ModuleConfig.light_model_name, max_tokens = 128, temperature = 0.0, n=1)
                    response = response[0] if type(response) == list and len(response) == 1 else response
                    assert "<output>" in response
                    break
                except:
                    try_num += 1
                    pass
            response = re.findall( r'<output>(.+)</output>', response)[0].strip()
            if "无需修改" not in response:
                self.context.set_origin_question(self.query)
                self.context.set_question(response)


            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ""
            self.log.info(
                "query rewrite success, use time {}s".format(round(time.time() - beginning_time, 2)))
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


if __name__ == "__main__":
    from include.utils.text_utils import get_md5
    lines = [ "本地有什么小吃被带火了", "特朗普在上任前任命了哪些关键职位的人员?", "清明出行人数"]
    # lines = [ "俄罗斯袭击乌克兰", "杭州房贷调息"]
    # lines = ["上海人均收入达到10000元" , "把新能源2000字的研报说明给我汇总一下"]
    for line in lines:
        query = line.strip()
        context = RagQAContext(session_id=get_md5(query))
        context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
        context.set_supply_info({"is_supply":False, "supply_info":["北京"]})
        context.set_basic_user_info({"User_Date":time.time(), "User_IP":'39.99.228.188'})
        # test1
        TimeLocRewrite(context).rewrite_query_with_supplyment()
        print("ori", context.get_origin_question())
        print("now", context.get_question())
        input()
    exit()

    # test2:
    query = "分析文档，输出不超过300字的报告"
    query = "把新能源2000字的研报说明给我汇总一下"
    query = "上海人均收入达到10000元"
    context = DocQAContext(session_id=get_md5(query))
    context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
    context.set_supply_info({"is_supply":False, "supply_info":["北京"]})
    context.set_basic_user_info({"User_Date":time.time(), "User_IP":'39.99.228.188'})
    TokenNumRewrite(context).rewrite_token_num_requirement()
    print("ori", context.get_origin_question())
    print("now", context.get_question())
    input()
