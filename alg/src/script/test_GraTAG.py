import requests
import json
import uuid
import traceback
import sys
import os
from datetime import datetime
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from include.utils.release_bot import env_test_release_bot,get_current_git_branch,env_test_release_bot_dingding





URL = 'xxx'

# 第一部分，互联网检索问答
def ainews_test_recommend_query():
    url = f"{URL}/execute"
    payload = json.dumps({
        "query": "美国大选"
    })
    headers = {
        'function': 'recommend_query',
        'request-id': 'test',
        'session-id': '51a65e97-3ab8-422e-9cce-d2a738da4cb9',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return json.loads(response.text)


def ainews_test_recommend_question():
    url = f"{URL}/execute"
    payload = json.dumps({})
    headers = {
        'function': 'recommend_question',
        'request-id': 'test',
        'session-id': '51a65e97-3ab8-422e-9cce-d2a738da4cb9',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(json.loads(response.text))
    return json.loads(response.text)


def ainews_test_supply_answer(_id, query, pro_flag):
    # 需自己控制payload中的参数传递,测试不同功能,比如pro_flag, @yhge
    url = f"{URL}/execute"

    payload = json.dumps({
        "user_id": "test1",
        "query": query,
        "qa_series_id": _id,
        "qa_pair_collection_id": _id,
        "type": "first",
        "pro_flag": pro_flag
    })
    headers = {
        'request-id': _id,
        'session-id': _id,
        'function': 'supply_question',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        return (True,json.loads(response.text))
    except Exception as e:
        return (False,response.text)


def ainews_test_answer(_id, query, ):
    # 注意pro，非pro版本标签由supply_question中生成context控制，这里测试逻辑需要注意 @yhge
    url = f"{URL}/stream_execute"

    payload = json.dumps({
        "qa_pair_collection_id": _id,
        "qa_series_id": _id,
        "qa_pair_id": _id,
        "query": query,
        "type": "first",
        "delete_news_list": [],
        "ip": "39.99.228.188",
        "user_id": "test1"
    })
    headers = {
        'function': 'answer',
        'request-id': _id,
        'session-id': _id,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload, stream=True)
    try:
        return_result = list()
        for chunk in response.iter_lines(chunk_size=1024, decode_unicode=False, delimiter=b"\0"):
            if chunk:
                content = chunk.decode('utf-8')
                if content.startswith("data: ") and content != "data: [DONE]\n\n":
                    content = content[len("data: "):]
                    content = json.loads(content.strip())
                    return_result.append(content)
                    continue
                else:
                    break
        final_answer = ""
        timeline_res = []
        recommendation_res = []
        print(len(return_result))
        for res_item in return_result[:]:
            if res_item["type"] == "text":
                if '<GraTAG type=\"image\" id=' not in res_item["data"]:
                    final_answer += res_item["data"]
            elif res_item["type"] == "timeline":
                timeline_res = res_item["data"]
            elif res_item["type"] == "recommendation":
                recommendation_res = res_item["data"]

        answer_dict = {
            "qa_answer": final_answer,
            "timeline": timeline_res,
            "recommendation_res": recommendation_res
        }
        return (True,answer_dict)
    except:
        return (False,response.text)


# _id_doc = str(uuid.uuid1())
_id_doc = "d0e08696-a185-11ef-9547-26d8c88445a0"
print(_id_doc)


# 第二部分，文档检索问答
def ainews_doc_test_supply_answer():
    url = f"{URL}/execute"

    payload = json.dumps({
        "user_id": "test1",
        "query": "对比两款不同品牌的电脑，评测它们的性能、价格及其他功能差异', '鉴别两种特定品牌饮料的味道、配方和营养含量。",
        "qa_series_id": _id_doc,
        "qa_pair_collection_id": _id_doc,
        "type": "first",
        "pro_flag": False
    })
    headers = {
        'request-id': _id_doc,
        'session-id': _id_doc,
        'function': 'doc_supply_question',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(json.loads(response.text))


def ainews_doc_test_answer():
    url = f"{URL}/stream_execute"

    payload = json.dumps({
        "qa_pair_collection_id": _id_doc,
        "qa_series_id": _id_doc,
        "qa_pair_id": _id_doc,
        "query": "总结一下这个文档中的内容",
        "type": "first",
        "delete_news_list": [],
        "ip": "39.99.228.188",
        "pro_flag": False,
        "pdf_names": "20240508_兴业证券*宏观专题*段超 卓泓 王笑笑 王轶君 彭华莹 郑兆磊 占康萍 金淳 于长馨 王祉凝 谢智勇*【兴证宏观】20240508-外乱内稳下的资产配置-兴业证券宏观",
        "pdf_ids": [
            "oss://public-xinyu/online-env/doc_search/test1/09f668cc9f19475b3ade79bda7411228.pdf"
        ],
        "search_mode": "doc",
        "user_id": "test1"
    })
    headers = {
        'function': 'doc_answer',
        'request-id': _id_doc,
        'session-id': _id_doc,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return_result = list()
    for chunk in response.iter_lines(chunk_size=1024, decode_unicode=False, delimiter=b"\0"):
        if chunk:
            content = chunk.decode('utf-8')
            if content.startswith("data: ") and content != "data: [DONE]\n\n":
                content = content[len("data: "):]
                content = json.loads(content.strip())
                return_result.append(content)
                continue
            else:
                break

    print(len(return_result))
    for i in return_result[:]:
        print(i)
    return return_result

if __name__ == '__main__':
    test_res_dict={
        "supply_answer_test_res":False,
        "pro_timeline_test_res":False,
        "pro_qa_answer_test_res":False,
        "pro_recommendation_test_res": False,
        "normal_qa_answer_test_res":False,
        "normal_recommendation_test_res":False
    }

    test_res_detail_dict={
        "supply_answer_test_res":"",
        "pro_timeline_test_res":"",
        "pro_qa_answer_test_res":"",
        "pro_recommendation_test_res": "",
        "normal_qa_answer_test_res":"",
        "normal_recommendation_test_res":""
    }
    # # test1 supply_answer
    _id = str(uuid.uuid1())
    query = "请比较中国两所高校"
    try:
        pass_symbol, supply_answer_res = ainews_test_supply_answer(_id, query, pro_flag=True)
        supply_answer_option=supply_answer_res["results"]["additional_query"]["options"]
        if len(supply_answer_option) > 1 and pass_symbol:
            test_res_dict["supply_answer_test_res"]=True
        else:
            test_res_detail_dict["supply_answer_test_res"]+=f"**query**:{query}\n**response**:{str(supply_answer_res)}"
    except Exception as e:
        print(traceback.format_exc())
        test_res_detail_dict["supply_answer_test_res"]+=f"**query**:{query}\n**response**:{traceback.format_exc()}"

    print("supply answer test done!")
    # test2 qa_answer pro
    _id = str(uuid.uuid1())
    query = "特朗普遭受枪击"
    try:
        _,supply_answer_res=ainews_test_supply_answer(_id,query,pro_flag=True)
        pass_symbol,answer_res=ainews_test_answer(_id,query)
        timeline_res=answer_res.get("timeline","")
        qa_answer_res=answer_res.get("qa_answer","")
        recommendation_res=answer_res.get("recommendation_res","")
        if  len(timeline_res) > 1 and pass_symbol:
            test_res_dict["pro_timeline_test_res"]=True
        else:
            test_res_detail_dict["pro_timeline_test_res"]+=f"**query**:{query}\n**response**:{str(answer_res)}"
        if len(qa_answer_res) > 1 and pass_symbol:
            test_res_dict["pro_qa_answer_test_res"]=True
        else:
            test_res_detail_dict["pro_qa_answer_test_res"]+=f"**query**:{query}\n**response**:{str(answer_res)}"
        if len(recommendation_res) > 1 and pass_symbol:
            test_res_dict["pro_recommendation_test_res"]=True
        else:
            test_res_detail_dict["pro_recommendation_test_res"]+=f"**query**:{query}\n**response**:{str(answer_res)}"
    except Exception as e:
        print(traceback.format_exc())
        test_res_detail_dict["pro_recommendation_test_res"]+=f"**query**:{query}\n**response**:{traceback.format_exc()}"
        test_res_detail_dict["pro_qa_answer_test_res"]+=f"**query**:{query}\n**response**:{traceback.format_exc()}"
        test_res_detail_dict["pro_timeline_test_res"]+=f"**query**:{query}\n**response**:{traceback.format_exc()}"

    print("qa_answer pro test done!")
    # test3 qa_answer none_pro
    try:
        _id = str(uuid.uuid1())
        query="特朗普遭受枪击"
        pass_symbol,supply_answer_res=ainews_test_supply_answer(_id,query,pro_flag=False)
        pass_symbol,answer_res=ainews_test_answer(_id,query)
        qa_answer_res=answer_res["qa_answer"]
        recommendation_res=answer_res["recommendation_res"]
        if len(qa_answer_res) > 1 and pass_symbol:
            test_res_dict["normal_qa_answer_test_res"]=True
        else:
            test_res_detail_dict["normal_qa_answer_test_res"]+=f"**query**:{query}\n**response**:{str(answer_res)}"
        if len(recommendation_res) > 1 and pass_symbol:
            test_res_dict["normal_recommendation_test_res"]=True
        else:
            test_res_detail_dict["normal_recommendation_test_res"]+=f"**query**:{query}\n**response**:{str(answer_res)}"
    except Exception as e:
        print(traceback.format_exc())
        test_res_detail_dict["normal_recommendation_test_res"]+=f"**query**:{query}\n**response**:{traceback.format_exc()}"
        test_res_detail_dict["normal_qa_answer_test_res"]+=f"**query**:{query}\n**response**:{traceback.format_exc()}"
    print("qa_answer none_pro test done!")

    # test4 doc_answer
    # print("answer_res",answer_res)
    # ainews_doc_test_supply_answer()
    # ainews_doc_test_answer()
    # print("answer_res",answer_res)


    # cal pass rate
    score=0
    test_detail=""
    test_name_map={
        "supply_answer_test_res":"问题补充",
        "pro_timeline_test_res":"PRO版本 时间线",
        "pro_qa_answer_test_res":"PRO版本 QA问答",
        "pro_recommendation_test_res": "PRO版本 追问推荐",
        "normal_qa_answer_test_res":"非PRO版本 QA问答",
        "normal_recommendation_test_res":"非PRO版本 追问推荐"
    }
    idx=1
    for key, val in test_res_dict.items():
        score += val
        if val:
            test_detail += f"✅ **{idx}. {test_name_map[key]} 测试通过**\n\n"
        else:
            test_detail += f"❌ **{idx}. {test_name_map[key]} 测试不通过**\n\n"
            test_detail += f"> 错误详情：{test_res_detail_dict.get(key, '无额外信息')}\n\n"
        idx += 1
    pass_rate=score/len(test_res_dict)


    # send messag
    branch_name = get_current_git_branch()
    if branch_name:
        branch_name="AINews:"+branch_name
        print(f"Current branch: {branch_name}")
    else:
        branch_name="None"
    if pass_rate==1:
        test_tile=f"发版测试通过:{branch_name}"
        color="green"
    else:
        test_tile = f"发版测试未通过:{branch_name}"
        color = "red"
    pass_rate_send = percentage = "{:.2%}".format(pass_rate)
    # 获取当前日期和时间
    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    env_test_release_bot_dingding(branch=branch_name,release_time=formatted_time,pass_rate=pass_rate_send,test_detail=test_detail,title=test_tile,title_color=color)


