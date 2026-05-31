# coding:utf-8
import os
import re
import copy
import json
import time
import traceback

import requests
import difflib
from functools import partial
from elasticsearch import Elasticsearch
from include.config import CommonConfig
import multiprocessing.dummy as multiprocessing
from include.logger import log
from concurrent.futures import ThreadPoolExecutor
from include.utils.abstract_utils import get_query_abstract
from include.rag.retrieval_utils import batchQueryDocCorrelationSeq,rerankBge
from include.decorator import timer_decorator
from include.utils.skywalking_utils import trace_new, record_thread
from azure.cognitiveservices.search.newssearch import NewsSearchClient
from msrest.authentication import CognitiveServicesCredentials
from datetime import datetime, timedelta
from include.utils.call_white_list import search_whitelist

SEARCH_TYPE_IAAR_DATABASE = "SEARCH_TYPE_IAAR_DATABASE"
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
current_directory = os.path.dirname(os.path.abspath(__file__))

headers_iaar_datebase = {
                'User-Agent': 'PostmanRuntime/7.39.0',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'token': IAAR_DataBase_config['access_key']
            }
RETRIEVAL_CODE = '44751c17-bd0c-49d9-8472-871bfd2f717e'

def query_iaar_news(raw_text, body_input=None):
    log.debug("query_iaar_news query:{}, body:{}".format(raw_text, body_input))
    flag = 0
    res_ans = []
    try:
        client = NewsSearchClient(endpoint="https://api.bing.microsoft.com",
                                  credentials=CognitiveServicesCredentials("2c7c3ce4e5ed43fc83d11e8e27fe9a5d"))
        client.config.base_url = '{Endpoint}/v7.0'  # Temporary change to fix the error

        news_result = client.news.search(query=body_input["keywords"],
                                         freshness=body_input.get('freshness', "Month"),
                                         market="zh-CN",
                                         sort_by="Relevance",
                                         count=100)  # sort_by= Relevance Date
        for tmp_news_result in news_result.value:
            strr = tmp_news_result.date_published
            tmp = {'chunk': tmp_news_result.description,
                   'content': tmp_news_result.description,
                   "id": tmp_news_result.url,
                   "images": {},
                   'publish_time': strr[0:10] + ' ' + strr[11:19],
                   "score": 1.0,
                   "site": tmp_news_result.provider[0].name,
                   "source": "bing news",
                   "summary": "",
                   "title": tmp_news_result.name,
                   "type": "bing_news",
                   'url': tmp_news_result.url,
                   # 'description': tmp_news_result.description,
                   # 'category': tmp_news_result.category,
                   # 'provider': tmp_news_result.provider[0].name
                   }
            res_ans.append(tmp)

        assert len(res_ans) > 0, "数据基座返回结果为空"

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        log.error("query_iaar_news error:{} 传入参数是:{}".format(e, body))
        flag = 1
    return res_ans, SEARCH_TYPE_IAAR_DATABASE, flag


def query_iaar_news_hot(raw_text, body_input=None):
    log.debug("query_iaar_news_hot query:{}, body:{}".format(raw_text, body_input))
    client = NewsSearchClient(endpoint="https://api.bing.microsoft.com",
                              credentials=CognitiveServicesCredentials("2c7c3ce4e5ed43fc83d11e8e27fe9a5d"))
    client.config.base_url = '{Endpoint}/v7.0'  # Temporary change to fix the error
    flag = 0
    res_ans = []
    try:
        # "ScienceAndTechnology", "Society", "Sports","World" ,"Auto",,"Business","China", "Education", "Entertainment", "Military", "RealEstate"
        for cat in ["Business","China", "Education", "Entertainment"]:
            news_result = client.news.category(category=cat, market="zh-CN", safe_search="strict")
            for tmp_news_result in news_result.value:
                strr = tmp_news_result.date_published
                tmp = {'chunk': tmp_news_result.description,
                       'content': tmp_news_result.description,
                       "id": tmp_news_result.url,
                       "images": {},
                       'publish_time': strr[0:10] + ' ' + strr[11:19],
                       "score": 1.0,
                       "site": tmp_news_result.provider[0].name,
                       "source": "bing news",
                       "summary": "",
                       "title": tmp_news_result.name,
                       "type": "bing_news",
                       'url': tmp_news_result.url
                       }
                res_ans.append(tmp)

        assert len(res_ans) > 0, "数据基座返回结果为空"

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        log.error("query_iaar_news_hot error:{} 传入参数是:{}".format(e, body))
        flag = 1
    return res_ans, SEARCH_TYPE_IAAR_DATABASE, flag


def query_iaar_news_hot_v2(raw_text, body=None):

    log.debug("query_iaar_news_hot_v2 , body:{}".format(body))
    flag = 0
    res = []
    max_retries = 2
    for retry in range(max_retries):
        try:
            url = IAAR_DataBase_config['url_topnews']
            headers = headers_iaar_datebase
            params = json.dumps(body)
            resp = requests.request('POST', url, headers=headers, data=params)
            # log.debug("resp.text:{}".format(resp.text))
            res0 = json.loads(resp.text)['results']
            res = []
            for r in res0:
                res.append({'chunk': r['summary'] if r['summary'] is not None else r['content'],
                            'content': r['content'],
                            "id": r['url'],
                            "images": r['images'],
                            'publish_time': r['publish_time'],
                            "score": 1.0,
                            "site": r['type'],
                            "source": "bing news",
                            "summary": r['summary'],
                            "title": r['title'],
                            "type": "bing_news",
                            'url': r['url']
                            })
            assert len(res) > 0, "数据基座返回结果为空"
            flag = 0
            return res, SEARCH_TYPE_IAAR_DATABASE, flag
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            if retry < max_retries - 1:
                log.warning("query_iaar_news_hot_v2 error:{} 传入参数是:{}".format(e, body))
                if 'start_date' in body and 'end_date' in body:
                    # 获取当前日期，30 天前的日期
                    current_date = datetime.now().date()
                    thirty_days_ago = current_date - timedelta(days=30)
                    current_date_str = current_date.strftime("%Y-%m-%d")
                    thirty_days_ago_str = thirty_days_ago.strftime("%Y-%m-%d")
                    body['start_date'] = thirty_days_ago_str
                    body['end_date'] = current_date_str
            else:
                log.error("query_iaar_news_hot_v2 error:{} 传入参数是:{}".format(e, body))
                res = f"query_iaar_news_hot_v2 error: {e}"
                flag = 1
    return res, SEARCH_TYPE_IAAR_DATABASE, flag


def query_iaar_detail(body=None, detail=True):
    """
        curl --location --request POST 'https://data.xinhua-news.cn/ChatSearch/search_news_es/' \
        --header 'Accept: application/json;charset=gb2312' \
        --header 'Content-Type: text/plain' \
        --data '{
            "searchKeyWords": "巴黎奥运会什么时候开幕"
        }'
        返回的数据在chunk中
    """
    log.debug("query_iaar_detail , body:{}".format(body))
    if IAAR_DataBase_config['is_demo']:
        keyy = {'q': json.dumps(body, ensure_ascii=False)} # {'q': json.dumps(body_fdc, ensure_ascii=False)
        config_res = search_whitelist(scheme_id=RETRIEVAL_CODE, input_info=keyy)
        if config_res is not None:
            log.debug("query_iaar_detail 使用了配置的结果,cnt={}".format(len(config_res[0]['output'])))
            flag = 0
            return config_res[0]['output'], SEARCH_TYPE_IAAR_DATABASE, flag
        else:
            log.debug("没有命中。")

    res=[]
    flag = 0
    max_retries = 1
    for retry in range(max_retries):
        try:
            if detail:
                url = IAAR_DataBase_config['url']
            else:
                url = IAAR_DataBase_config['summary_url']
            headers = headers_iaar_datebase
            params = json.dumps(body)
            resp = requests.request('POST', url, headers=headers, data=params)
            res = json.loads(resp.text)['results']
            # 如果是详情接口，则返回online部分
            if 'search_type' in body:
                res = res['online']
            assert len(res) > 0, "数据基座返回结果为空"
            flag = 0
            if not detail:
                for res_i in res:
                    res_i['summary'] = '「SUMMARY」' + res_i.get('summary', '')
            return res, SEARCH_TYPE_IAAR_DATABASE, flag
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            if retry < max_retries - 1:
                log.warning("query_iaar_detail error:{} 传入参数是:{}".format(e, body))
                if 'start_date' in body['online_search'] and 'end_date' in body['online_search']:
                    del body['online_search']['start_date']
                    del body['online_search']['end_date']
            else:
                log.error("query_iaar_detail error:{} 传入参数是:{}".format(e, body))
                res = f"query_iaar_detail error: {e}"
                flag = 1
    return res, SEARCH_TYPE_IAAR_DATABASE, flag


def query_iaar_database(raw_text, body=None, pro_flag=True):
    """
        curl --location --request POST 'https://data.xinhua-news.cn/ChatSearch/search_news_es/' \
        --header 'Accept: application/json;charset=gb2312' \
        --header 'Content-Type: text/plain' \
        --data '{
            "searchKeyWords": "巴黎奥运会什么时候开幕"
        }'
    """
    news_type = body.get('news_type', 0)
    if news_type == 'news' and pro_flag:  # TODO: 目前只要是非pro模式，都不开启其他检索通道
        if 'news_type' in body:
            del body['news_type']
        res = query_iaar_detail(body)
        for r in res[0]:
            r['type'] = "bing_news"
        return res
    elif news_type == 'hot_news' and pro_flag:
        if 'news_type' in body:
            del body['news_type']
        if IAAR_DataBase_config['use_iaar_hot_news']:
            return query_iaar_news_hot_v2(raw_text, body)
        else:
            return query_iaar_news_hot(raw_text, body)
    else:
        body.update({"queries": raw_text})
        if 'news_type' in body:
            del body['news_type']
        if "keywords" in body:
            del body['keywords']
        return query_iaar_detail(body, pro_flag)


if __name__ == "__main__":
    body = {'search_type': ['online'], 'online_search': {'max_entries': 12, 'cache_switch': True, 'baidu_field': {'switch': False, 'mode': 'relevance', 'type': 'page'}, 'bing_field': {'switch': True, 'mode': 'relevance', 'type': 'page_web'}, 'sogou_field': {'switch': False, 'mode': 'relevance', 'type': 'page'}, 'start_date': '2020-10-01', 'end_date': '2020-12-31'}, 'request_id': 'gyhtest', 'queries': '对2020年第四季度安徽省第一产业增加值进行数据解读'}
    res = query_iaar_detail(body)
    print(res[0])

