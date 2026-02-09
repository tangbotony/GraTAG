# 获取摘要
# coding:utf-8
import json
import os
import sys
import datetime
import requests
import traceback
from include.logger import log
from include.config import PromptConfig, RagQAConfig, QueryIRConfig
from include.utils import llm_call
from include.decorator import timer_decorator


def get_query_abstract(input_lines, write_len=50):
    """
    摘要任务
    :param input_lines: 待摘要的任务
    :param write_len: 期望输出摘要的文本长度
    :return: target_output_item string: 输出的文本摘要
    """

    # 如果选定内小于3000个中文，抛出异常
    if len(input_lines) >= 3000:
        log.info("message:{}".format(json.dumps(
            {
                "function": "text_abstract",
                "info": "text_abstract too long!",
                "code": "text_abstract too long!",
                "reason": "/"
            })
            , ensure_ascii=False))

    # 载入预定义的PROMPT模版
    instruction_temp = PromptConfig["basic_abstract_task"]['instruction']
    input_temp = PromptConfig["basic_abstract_task"]['input_item']

    # 大模型输入的实例化文本
    input_final = input_temp.format(all_content=input_lines,
                                    write_len=write_len,
                                    write_style="新华社",
                                    page_title="")
    prompt = instruction_temp + input_final
    response = llm_call(query=prompt, task_name="文本摘要任务",
                        model_name=RagQAConfig['TASK_MODEL_CONFIG']['query_abstract'], n=1, temperature=0.7, top_p=1.0, max_tokens=4086, show=True)
    return response



@timer_decorator
def news_retrieval_summary(query="", clogger=log):
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(
        days=-QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["time_range"])).strftime('%Y-%m-%d')
    return_num = 2
    try:
        url = QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["url"]
        headers = {'token': QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["token"],
                   'Content-Type': 'application/json'}
        payload = {
            "request_id": "",
            "queries": query,
            "return_num": return_num,
            "start_date": start_date,
            "end_date": end_date,
            "baidu_field": {
                "switch": False,
                "type": "news"
            },
            "bing_field": {
                "switch": True,
                "type": "news"
            },
            "sogou_field": {
                "switch": False,
                "type": "news"
            }
        }
        while return_num > 0:
            try:
                time_out = 1 if return_num > 1 else 200
                response = requests.request("POST", url, headers=headers, json=payload, timeout = time_out)
                assert response.status_code == 200, response.reason
                break
            except:
                return_num -= 1
        response = json.loads(response.text)
        retrieval_result = response['results']
        return retrieval_result
    
    except Exception as e:
        traceback.print_exc()
        clogger.warning(
            "news_retrieval_summary occur error：{}\nDefault result as {{\"is_event_related\": False}}.".format(str(e)))        


if __name__ == "__main__":
    test_line = ("“老坛工艺，足时发酵”，这是多家方便面的供货商宣称的“秘籍”。"
                 "然而，所谓的“老坛”，是土坑；“足时”，是“足式”……插旗菜叶酸菜，"
                 "是“老坛新酒”，还是“新瓶装旧酒”，多年以来一直在蒙蔽消费者。"
                 "食品生产者不能为了利益，就抛弃良心。只有守住底线，才能赢得消费者的青睐。"
                 "笔者认为，莫把消费者当“韭菜”，要对得起消费者的信任。人无信不立，业无信不兴。")
    ans = get_query_abstract(test_line)
    print(ans)
