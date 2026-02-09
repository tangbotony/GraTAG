import json
import requests
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.config import CommonConfig
from include.utils.time_utils import now_date


def search_whitelist(scheme_id:str, input_info:dict) -> json:
    url = CommonConfig["WHITE_LIST"]["search_url"]
    payload = json.dumps({
            "scheme_type":scheme_id,
            "input":input_info
            })
    headers = {
        'token': 'xxx',
        'Content-Type': 'application/json',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response =  json.loads(response.text)["results"]
    return  response


def create_whitelist(scheme_id:str, input_info:dict, output_info:dict) -> json:
    url = CommonConfig["WHITE_LIST"]["create_url"]
    date = now_date()
    payload = json.dumps({
            "scheme_type":scheme_id,
            "input":input_info,
            "output":output_info,
            "created_at": date,
            "updated_at": date
            })
    headers = {
        'token': 'xxx',
        'Content-Type': 'application/json',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response =  json.loads(response.text)
    return  response



def del_whitelist(id_list:list) -> json:
    url = CommonConfig["WHITE_LIST"]["del_url"]
    date = now_date()
    payload = json.dumps({
            "ids":id_list
            })
    headers = {
        'token': 'xxx',
        'Content-Type': 'application/json',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response = json.loads(response.text)
    return  response


def update_whitelist(id:str, scheme_id:str, input_info:dict, output_info:dict) -> json:
    url = CommonConfig["WHITE_LIST"]["update_url"]
    date = now_date()
    payload = json.dumps({
            "id":id,
            #"scheme_type":scheme_id,
            "input":input_info,
            "output":output_info,
            # "created_at": date,
            # "updated_at": date
            })
    headers = {
        'token': 'xxx',
        'Content-Type': 'application/json',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response = json.loads(response.text)
    return  response


if __name__ == "__main__":
    from include.config import RagQAConfig
    del_whitelist(['a3c045c2-c988-4e65-bcdf-0730eda00140', 'ac5b5af9-0806-4e5b-8308-0e38804cb595',
                   '18951334-d5df-4c2c-9998-39ee56314895', '934653f0-65e4-4041-bc3c-be1d88c70904'])
    whitelist_response = search_whitelist(
        scheme_id=RagQAConfig["WHITE_LIST_CONFIG"]["query_answer"]["scheme_id"],
        input_info={"query": '2024年06月26日上海有什么新闻？其中哪些新闻是关于房地产的？'})

    scheme_id = "xxx"
    input_info = {
        "query":"如何看待姜萍事件的始末？"
    }
    res = search_whitelist(scheme_id=scheme_id, input_info=input_info)
    print(res[0]["output"])

    exit()
    scheme_id = "xxx"
    input_info = {
        "query":"last_test",
        "supplyment":"",
        "split_num":3
    }
    output_info = {
        "is_complex":"False",
        "sub_questions":[]
    }
    res = create_whitelist(scheme_id=scheme_id, input_info=input_info, output_info = output_info)
    print(res)