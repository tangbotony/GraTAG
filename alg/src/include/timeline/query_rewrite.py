import time
import traceback
import datetime
from multiprocessing.dummy import Pool as ThreadPool

from include.logger import log
from include.utils.llm_caller_utils import llm_call
from include.utils.similarity_utils import get_similarity
from include.config import PromptConfig, TimeLineConfig
import re
import json
from include.utils import clean_json_str

def get_rewrite_query(ori_query, model_name=TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["query_rewrite"], clogger=log):
    '''
    对用户输入问题进行改写，返回3个时间线问题
    :return: rewrite_query:  {"is_timeline_query": False, "dimension": "地点发展或物品发展", "timeline_queries": ["上海各区的形成与发展历程", "上海浦东新区的发展历史", "上海历史上的行政区划变迁"]}
    '''
    current_date = datetime.datetime.now().date()
    if 'qwen' in model_name:
        task_prompt_template = PromptConfig["timeline_query_rewrite"]["QWEN_input_item"] #QWEN_input_item or GPT_input_item
    else:
        task_prompt_template = PromptConfig["timeline_query_rewrite"]["GPT_input_item"] #QWEN_input_item or GPT_input_item

    query = task_prompt_template.format(str(current_date), str(ori_query))
    rewrite_query = {"is_timeline_query": False, "dimension": "", "timeline_queries": [str(ori_query)]} #兜底返回原始query
    retry_cnt = 0
    max_try_cnt = 3  #最大尝试次数
    while True:
        try:
            response = llm_call(query=query, model_name=model_name, clogger=clogger)
            response = json.loads(clean_json_str(response))
            assert isinstance(response, dict), "时间线问题改写模型输出格式不符合预期"
            assert "原问题是否是一个时间脉络梳理问题" in response, "时间线问题改写模型输出缺少判断"
            assert "维度" in response, "时间线问题改写模型输出缺少维度"
            assert "时间线问题" in response, "时间线问题改写模型输出缺少重写问题"

            if response["原问题是否是一个时间脉络梳理问题"] == "是":  #
                rewrite_query["is_timeline_query"] = True
            rewrite_query["dimension"] = str(response["维度"])
            rewrite_query_list = []
            for query_item in response["时间线问题"]:
                rewrite_query_list.append(list(query_item.values())[0])
            assert (len(rewrite_query_list) >= 3 and len(rewrite_query_list[0]) >= 5), "时间线问题改写模型问题格式错误"
            rewrite_query["timeline_queries"] = rewrite_query_list
            break

        except Exception as e:
            clogger.warning(
                "get_rewrite_query occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(),
                                                                                          retry_cnt,
                                                                                          max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                clogger.warning(
                    "get_rewrite_query occurs error: {}, retry cnt:{}/{}, return {{}}.".format(e, retry_cnt,
                                                                                               max_try_cnt))
                break
    return rewrite_query


if __name__ == "__main__":
    init_question = "上海有多少个区？每个区各有什么特点？"
    rewrite_query = get_rewrite_query(init_question)
    print('rewrite_query', rewrite_query)
