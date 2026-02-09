import sys
import traceback
from string import Template
from concurrent.futures import ThreadPoolExecutor
from include.logger import ContextLogger
from include.config import ModuleConfig
from include.utils import llm_call
from include.utils import check_stepback
from include.utils.post_processer import postprocess_multisplit_queries

def get_FunctionCall_judge(question: str, log:ContextLogger = None, max_try: int = 2, model_name: str = ModuleConfig.light_model_name):
    """
    判定输入的问题是否需要调用函数工具
    Args:
        输入：
            question: 问题内容
            max_try: 尝试拆分次数
        输出：
            返回 None 表示不需要调用功函数
            返回 dict 指示回答本问题需要调用的函数
    """
    JudgeWeatherTemplate = ModuleConfig["JudgeWeatherTemplate"]

    dic = {
        "original_query": question
    }
    prompt = Template(JudgeWeatherTemplate).substitute(dic)

    res = None
    try_num = 0
    response = None
    while try_num < max_try:
        try:
            response = llm_call(
                    query=prompt,
                    model_name=model_name, 
                    add_template = False,
                    n=1,
                    max_tokens = 10
                    )
            assert ("True" in response or "False" in response)
            res = response
            break
        except:
            try_num += 1
            pass
    if res != None:
        return "True" in res
    else:
        log.error(f"Function get_FunctionCall_judge failed call LLM. Query:{question}. LLM_return:{response}. ")


def get_StepBack_judge(question: str, log:ContextLogger = None, max_try: int = 2, model_name: str = ModuleConfig.light_model_name):
    """
    判定输入的问题是否需要做回退处理，如果需要则返回处理后的问题形式
    Args:
        输入：
            question: 问题内容
            max_try: 尝试拆分次数
        输出：
            返回 None 表示不需要问题回退
            返回 字符串 是回退的新问题
    """
    JudgeStepBackTemplate = ModuleConfig["JudgeStepBackTemplate"]
    dic = {
        "original_query": question
    }
    prompt = Template(JudgeStepBackTemplate).substitute(dic)

    new_query = None
    try_num = 0
    response = None
    while try_num < max_try:
        try:
            response = llm_call(
                    query=prompt,
                    model_name=model_name,  
                    add_template = True,
                    n=1
                    )
            post_response = postprocess_multisplit_queries([response])
            assert post_response != []
            response = post_response[0]
            assert len(response) < 50
            new_query = response
            break
        except:
            try_num += 1
            pass
    return new_query


def get_NeedRag_judge(question: str, log:ContextLogger = None, max_try: int = 2, model_name: str = ModuleConfig.light_model_name):
    """
    判定输入的问题是否需要调用检索功能(Rag)
    Args:
        输入：
            question: 问题内容
            max_try: 尝试拆分次数
        输出：
            True 表示需要调用Rag
            False 表示不需要
    """
    JudgeNeedRagTemplate = ModuleConfig["JudgeNeedRagTemplate"]
    dic = {
        "original_query": question
    }
    prompt = Template(JudgeNeedRagTemplate).substitute(dic)
    try_num = 0
    res = None
    response = None
    while try_num < max_try:
        try:
            response = llm_call(
                    query=prompt,
                    model_name=model_name,
                    add_template = True,
                    n=1,
                    max_tokens = 10
                    )
            assert len(response) < 6
            res = response
            break
        except:
            try_num += 1
            pass
    if res != None and ("True" in res or "False" in res):
        return "True" in res
    else:
        log.error(f"Function get_NeedRag_judge failed call LLM. Query:{question}. LLM_return:{response}. exc_info: {str(sys.exc_info())}, format_exc: {str(traceback.format_exc())}")



def judge_process(query:str, log:ContextLogger = None, check_func_call:bool = False, check_step_back:bool = False, check_need_rag:bool = False):  
    """
    对输入的query做函数调用需求判断、回退判断、rag需求判断
    Args:
        query 问题文本
    output:
        json--> {
                    "query_info": {
                            "type": "ori_query",
                            "query": XXXXXX,
                            "FunctionCall":None,
                            "need_rag":False
                        },
                    "stepback_info": stepback_query_json
                }
    """
    query_json = {
        "type": "ori_query",
        "query": query,
        "FunctionCall":None,
        "need_rag":False
    }
    stepback_query_json = None
    func_call, stepback_query, if_rag = False, None, True
    try:
        with ThreadPoolExecutor() as executor:
            if check_func_call:
                func_call = executor.submit(get_FunctionCall_judge, query, log = log)
            if check_step_back:
                stepback_query = executor.submit(get_StepBack_judge, query, log = log)
            if check_need_rag:
                if_rag = executor.submit(get_NeedRag_judge, query, log = log)

            if check_func_call:
                func_call = func_call.result()
            if check_step_back:
                stepback_query = stepback_query.result()
            if check_need_rag:
                if_rag = if_rag.result()
    except Exception as e:
        log.error(f"Judge_process failed. exc_info: {str(sys.exc_info())}, format_exc: {str(traceback.format_exc())}")

    # 函数判定
    if func_call:
        query_json["FunctionCall"] = func_call
        result = {
                "query_info": query_json,
                "stepback_info": stepback_query_json
                }
        return result
    
    # 回退判定
    if stepback_query and check_stepback(query, stepback_query):
        stepback_query_json = {
            "type": "stepback_query",
            "query": stepback_query,
            "FunctionCall": None,
            "need_rag": False
        }
        # 由于时间消耗的问题，回退如果成功，直接确定该问题需要Rag，不需判断。
        # if_rag = get_NeedRag_judge(stepback_query)
        # if if_rag:
        #     stepback_query_json["need_rag"] = True
        stepback_query_json["need_rag"] = True
        result = {
                "query_info": query_json,
                "stepback_info": stepback_query_json
                }
        log.info(f"query 回退重写成功，原query:{query}, 回退后query:{stepback_query}")
        return result

    # rag判定
    if if_rag:
        query_json["need_rag"] = True 

    result = {
        "query_info": query_json,
        "stepback_info": stepback_query_json
    }
    return result



if __name__ == "__main__":
    from include.utils.text_utils import get_md5
    from include.context import RagQAContext
    query = "年轻人想创业，需要做哪些准备？"
    context = RagQAContext(session_id=get_md5(query))
    context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
    log = ContextLogger(context)

    res = get_FunctionCall_judge("娜塔莉·波特曼学习中文对她的个人生活产生了哪些影响？", log = log)
    print(res)