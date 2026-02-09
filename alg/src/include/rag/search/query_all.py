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
from include.utils.skywalking_utils import trace_new
from include.rag.search.query_iaar import query_iaar_database
from include.utils.milvus_utils import load_from_milvus, query_embedding

auth_config = CommonConfig['AUTH_CONFIG']
# baidu_config = CommonConfig['BAIDU']
fschat_config = CommonConfig['FSCHAT']
# search_summary_service = CommonConfig['SEARCH_SUMMARY_SERVICE']
search_xinhua = CommonConfig['XINHUA']
ner_config = CommonConfig['NER']
similarity_config = CommonConfig['SIMILARITY_CONFIG']
rerank_config = CommonConfig['RERANK']
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
current_directory = os.path.dirname(os.path.abspath(__file__))

valid_urls = set()
with open(os.path.join(current_directory, 'valid_urls.txt')) as file:
    for line in file:
        valid_urls.add(line.strip())


def is_404(url):
    try:
        response = requests.get(url)
        return response.status_code == 404
    except requests.exceptions.RequestException:
        return True


def check_url(url):
    return True
    result = is_404(url)
    if result == True:
        return True
    else:
        return False


def is_valid_url(url: str):
    # 判断url是否来自可信网站
    parsed_url = urlparse(url)
    return parsed_url.netloc in valid_urls


headers = {"token": auth_config['key'],
           'Content-Type': 'application/json', }

sim_scores_service = fschat_config["general_url"]
search_keywords_service = ner_config["keyword_url"]
# search_baidu_service = baidu_config['url']
# search_summary_service = search_summary_service["url"]
search_xinhua_url = search_xinhua["url"]

search_type_baidu = "baidu"
search_type_es_crawled = "es_crawled "
search_type_search_summary = "search_summary"
search_type_es_xinhua = "es_xinhua"
search_type_credible = "credible"
search_type_xinhua_vector_db = "xinhua_vector_db"
search_type_xinhua_search_news_es = "xinhua_search_news_es"
SEARCH_TYPE_XINHUA_ES_MILVUS = "SEARCH_TYPE_XINHUA_ES_MILVUS"
SEARCH_TYPE_XINHUA_FAKE = "SEARCH_TYPE_XINHUA_FAKE"
SEARCH_TYPE_XINHUA_INNER = "SEARCH_TYPE_XINHUA_INNER"
SEARCH_TYPE_IAAR_DATABASE = "SEARCH_TYPE_IAAR_DATABASE"
from urllib.parse import urlparse


def remove_html_tags(html):
    return re.sub(r'<[^>]+>', '', html)


def log_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        # log.info(f"Time taken by {func.__name__}: {end_time - start_time} seconds")
        return result

    return wrapper


# TODO: time
# TODO: xinhua ES
# TODO: wendao db

def get_search_keywords(raw_text, timeout=120):
    try:
        payload = json.dumps({"s": [raw_text]})
        res_temp = requests.request(
            "POST", CommonConfig['NER']["keyword_url"],
            headers={"token": CommonConfig['AUTH_CONFIG']['key'], 'Content-Type': 'application/json', }, data=payload, timeout=timeout)
        all_res_json = res_temp.json()[0]
    except Exception as e:
        print(traceback.print_exc())
        return [raw_text]
    return all_res_json


def get_sim_scores(query, docs):
    docs = [line[0:1024] for line in docs]
    payload = {
        "model": similarity_config["baai_sim_general"],
        "params": {
            "request_id": "",
            'text_a': ["为这个句子生成表示以用于检索相关文章：" + query],
            'text_b': docs
        }
    }
    headers = {
        "token": auth_config['key'],
    }
    response = requests.request("POST", sim_scores_service, headers=headers, json=payload)
    return json.loads(response.text)['response']

def query_xinhua_vector_db(raw_text, body=None, **kwargs):
    """
        curl --location --request POST 'https://data.xinhua-news.cn/ChatSearch/search_news_emb/' \
        --header 'Accept: application/json;charset=gb2312' \
        --header 'Content-Type: text/plain' \
        --data '{
            "searchKeyWords": "巴黎奥运会什么时候开幕"
        }'
    """
    flag = 0
    try:
        if "searchKeyWords" not in body.keys():
            body["searchKeyWords"] = raw_text
    except Exception as e:
        log.warning(e)
        body = {"searchKeyWords":raw_text}
    try:
        # 发起POST请求
        res = requests.post(
            url=search_xinhua['vector_db_url'],
            json=body,
            headers={
                "Accept": "application/json;charset=gb2312",
                "Content-Type": "text/plain"},
            timeout=30
        ).json()

        res = list(res['result']['res'])

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        error = f"query_credible error {e}"
        log.error(error)
        res = f"query_credible_error: {error}"
        flag = 1
    return res, search_type_xinhua_vector_db, flag

def query_xinhua_search_news_es_kwargs(raw_text, body=None, **kwargs):
    """
        curl --location --request POST 'https://data.xinhua-news.cn/ChatSearch/search_news_es/' \
        --header 'Accept: application/json;charset=gb2312' \
        --header 'Content-Type: text/plain' \
        --data '{
            "searchKeyWords": "巴黎奥运会什么时候开幕"
        }'
    """
    flag = 0
    if not body:
        body = {"searchKeyWords": raw_text}
    try:
        # 发起POST请求
        res = requests.post(
            url=search_xinhua['search_news_es_url'],
            json=body,
            headers={
                "Accept": "application/json;charset=gb2312",
                "Content-Type": "text/plain"}
        ).json()

        res = list(res['result'])
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        error = f"query_credible error {e}"
        log.error(error)
        res = f"query_credible_error: {error}"
        flag = 1
    return res, search_type_xinhua_search_news_es, flag

@timer_decorator
def parse_docId(resAns):
    docIdList = []
    for rr in resAns:
        docId = rr['docId']
        docIdList.append(docId)
    return docIdList

def xinhua_access_token():
    # 测试环境获取token的url
    # url = "http://service-dsj.inserv.xhtxs.net/data/base/getToken"
    # 正式环境获取token的url
    url = 'http://service.data.xinhua-news.cn/data/base/getToken'
    payload = {"appId": search_xinhua["app_id"], "accessKey": search_xinhua["access_key"]}
    try:
        r = requests.get(url, params=payload)
        return r.json()['access_token']
    except Exception:
        raise (Exception("Exception when request the token"))


def xinhua_search(query):
    '''
    :param query: 自定义query，添加更多查询条件，格式参考es python api
    :return: 结果dict
    '''
    flag = 0
    body = json.dumps(query['paramJson'])
    try:
        '''
        res_temp = {"code": "1200","message": "success",
        "lastSearchExpr": "{\"queryDsl\":\"{ \\\"bool\\\" : { \\\"must\\\" : [ { \\\"bool\\\" : { \\\"must\\\" : [ { \\\"bool\\\" : { \\\"should\\\" : { \\\"match\\\" : { \\\"headLine.cn\\\" : { \\\"query\\\" : \\\"环境\\\", \\\"type\\\" : \\\"boolean\\\", \\\"analyzer\\\" : \\\"synonym_jieba_analyzer\\\", \\\"boost\\\" : 10.0, \\\"minimum_should_match\\\" : \\\"30%\\\" } } } } }, { \\\"match\\\" : { \\\"keywords\\\" : { \\\"query\\\" : \\\"水污染\\\", \\\"type\\\" : \\\"boolean\\\", \\\"analyzer\\\" : \\\"synonym_whitespace_analyzer\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"match\\\" : { \\\"authors\\\" : { \\\"query\\\" : \\\"倪元锦\\\", \\\"type\\\" : \\\"boolean\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"match\\\" : { \\\"issuerDept\\\" : { \\\"query\\\" : \\\"国内部-总编室\\\", \\\"type\\\" : \\\"boolean\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"match\\\" : { \\\"languageId\\\" : { \\\"query\\\" : \\\"zh-CN\\\", \\\"type\\\" : \\\"boolean\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } } ], \\\"filter\\\" : [ { \\\"match\\\" : { \\\"keywords\\\" : { \\\"query\\\" : \\\"水污染\\\", \\\"type\\\" : \\\"boolean\\\", \\\"analyzer\\\" : \\\"synonym_whitespace_analyzer\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"match\\\" : { \\\"authors\\\" : { \\\"query\\\" : \\\"倪元锦\\\", \\\"type\\\" : \\\"boolean\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"match\\\" : { \\\"issuerDept\\\" : { \\\"query\\\" : \\\"国内部-总编室\\\", \\\"type\\\" : \\\"boolean\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"match\\\" : { \\\"languageId\\\" : { \\\"query\\\" : \\\"zh-CN\\\", \\\"type\\\" : \\\"boolean\\\", \\\"minimum_should_match\\\" : \\\"0%\\\" } } }, { \\\"range\\\" : { \\\"issueDateTime\\\" : { \\\"from\\\" : \\\"2015-03-01 01:03:37\\\", \\\"to\\\" : \\\"2017-04-01 01:03:37\\\", \\\"include_lower\\\" : true, \\\"include_upper\\\" : true } } }, { \\\"range\\\" : { \\\"createDateTime\\\" : { \\\"from\\\" : \\\"2015-01-01 01:03:37\\\", \\\"to\\\" : \\\"2017-04-01 01:03:37\\\", \\\"include_lower\\\" : true, \\\"include_upper\\\" : true } } } ] } }, { \\\"wrapper\\\" : { \\\"query\\\" : \\\"eyAi....lIH0gfSB9IF0gfX0=\\\" } } ] }}\",\"sortType\":\"createDateTime+\",\"returnFields\":\"symbol,docId,docLibId,headLine,content,keywords,authors,knowledgeTag,richNames,issuer,issuerDept,source,searchCategoryId,createDateTime,mediaTypeId,languageId,broadcastDate,wordCount,issueDateTime,level\"}",
        "analyzedSearchWords":"","total": 1,
        "data":[{
        "symbol": "XxjdzbC000045_20170210_BJTFN0.xml",
        "broadcastDate": "2017-02-10 15:52:22",
        "issuerDept": "国内部-总编室",
        "keywords": "水污染",
        "wordCount": 661,
        "level": 1,
        "docId": "2000120170212999999061",
        "languageId": "zh-CN",
        "source": "北京分社",
        "content": "　　新华社北京２月１０日电（记者倪元锦）北京市环保局１０日召开发布会称，２０１６年查处水环境违法行为２２０起，处罚金额达３９８１．８１万元。\n　　北京市环境监察总队副总队长谢志宽介绍，２０１６年，环保部门围绕重点流域水体水质改善，执法重点涵盖“排入地表排污单位”“城镇污水处理厂”“工业园区集中污水处理设施”“垃圾填埋场”“畜禽养殖场”等，严厉查处一批具有典型意义的环境违法案件。\n　　１０日，北京市环境监察总队对“２０１６年涉水环境违法十起典型案例”进行曝光，违法行为集中表现为“污染物超标排放”“未按规定建设、运行水污染治理设施”“以漫流方式排放、倾倒污水”“畜禽养殖企业未按规定处置畜禽粪便”等。\n　　北京市环境监察总队综合稽查科科长王延奎称，“污染物超标排放”的违法案例居多。例如，北京洳河污水处理有限公司总排口出水浑浊，污水处理厂超标排放；六里屯垃圾填埋场的总排口水污染物超标，其处理过程中产生高浓度渗滤液，排放前处理未达标；北京千喜鹤食品有限公司的屠宰废水超标，未经先期处理排入市政管网；丽都饭店有限公司餐饮污水超标排入市政管网，应规范安装隔油池；北京慧诚房地产开发有限公司生活污水超标排入地表环境。\n　　此外，１０日通报的其他类型的水环境违法案例有：北京悦丽汇医疗美容诊所有限公司未对医疗机构污水进行预处理，污水直排市政管网；北京蓝天绿茵污水处理有限公司，氨氮自动监控数据为０，自动监控设施未正常运转；北京市新达世纪树脂有限责任公司厂区坑道有清洗罐釜的乳白色生产废水，以漫流方式排入没有防渗措施的坑道污染土壤。（完）",
        "issuer": "徐兆荣1",
        "createDateTime": "2017-02-12 15:26:17",
        "searchCategoryId": "c58,c02701,c2102,c20001001,c025,c0244047,c026,c5801,c027,c5803,c23039,c0260001,c0250001,c1,c2,c0270082,c0030002016,c0244039,c21,c210201,c0030002,c0241002,c23",
        "headLine": "（环境）北京：２０１６年查处水环境违法２２０起罚金近４０００万元",
        "docLibId": 3,
        "mediaTypeId": "Text",
        "issueDateTime": "2017-02-10 15:52:21",
        "authors": "倪元锦"
        }]}
        '''
        # print("="*50,body)
        access_token = xinhua_access_token()
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        params_xinhua = {"access_token": access_token}
        query = {"access_token": access_token, "paramJson": body}
        res_temp = requests.request("POST", search_xinhua_url + "?access_token=" + access_token,
                                    data=query, timeout=10).json()
        # '''
        # 加入判断是否为正确的
        # print("a"*50)
        if res_temp["code"] != "1200" and res_temp["code"] != "1901":
            # print("="*50)
            flag = 1
            res = res_temp["code"] + res_temp["message"]
            return res, search_type_es_xinhua, flag
        else:
            # print("-"*50)
            res = res_temp["data"]
            for i in range(len(res)):
                res[i]['total'] = res_temp.get('total')
    except Exception as e:
        error = f"xinhua_search error {e}"
        log.error(error)
        res = f"xinhua_search error: {error}"
        flag = 1
    return res, search_type_es_xinhua, flag


def xinhua_search_new(query, **kwargs):
    '''
    :param query: 自定义query，添加更多查询条件，格式参考es python api
    :return: 结果dict
    '''
    flag = 0
    try:
        body = json.dumps(query['paramJson'])
        headers = {'Content-Type': 'text/plain', "Accept": "application/json;charset=gb2312"}
        res_temp = requests.request("POST", search_xinhua_url, headers=headers,
                                    data=body, timeout=10).json()

        if res_temp["code"] != "1200" and res_temp["code"] != "1901":
            # print("="*50)
            flag = 1
            res = res_temp["code"] + res_temp["message"]
            return res, search_type_es_xinhua, flag
        else:
            # print("-"*50)
            res = res_temp["data"]
            for i in range(len(res)):
                res[i]['total'] = res_temp.get('total')
    except Exception as e:
        error = f"xinhua_search error {e}"
        log.error(error)
        res = f"xinhua_search error: {error}"
        flag = 1
    return res, search_type_es_xinhua, flag

def xinhua_search_es_20240524(query):
    '''
    :param query: 自定义query，添加更多查询条件，格式参考es python api
    :return: 结果dict
    '''
    # body3 = json.dumps(query['paramJson'])
    # headers = {'Content-Type': 'text/plain', "Accept": "application/json;charset=gb2312"}
    # url = 'http://172.22.73.84:7676/search_news_es/'
    # res_temp = requests.request("POST", url, headers=headers, data=body3, timeout=10).json()
    # print(res_temp)


    flag = 0
    url = "http://172.22.73.84:7676/search_news_es/"
    try:
        body = json.dumps(query['paramJson'])
        headers = {'Content-Type': 'text/plain', "Accept": "application/json;charset=gb2312"}
        log.debug('header:{}'.format(headers))
        log.debug("url:{}".format(url))
        log.debug("body:{}".format(body))
        res_temp = requests.request("POST", url, headers=headers,data=body, timeout=10).json()
        print(res_temp)
        if res_temp["code"] != "1200" and res_temp["code"] != "1901":
            # print("="*50)
            flag = 1
            res = res_temp["code"] + res_temp["message"]
            return res, search_type_es_xinhua, flag
        else:
            # print("-"*50)
            res = res_temp["data"]
            for i in range(len(res)):
                res[i]['total'] = res_temp.get('total')
    except Exception as e:
        error = f"xinhua_search error {e}"
        log.error(error)
        res = f"xinhua_search error: {error}"
        flag = 1
    return res, search_type_es_xinhua, flag


# es检索过滤 700 个网页
def filter_es_700(es_result):
    res = []
    for item in es_result:
        url = item.get('url')
        if not url:
            continue
        if is_valid_url(url):
            res.append(item)
    return res


# 把五个返回对齐，list返回，加入log
@timer_decorator
def query_all(raw_text, user_info=None, query_kwargs=None, pro_flag=True, topk=100):
    """
    :param raw_text: 待查询文本
    :param user_info: 请求的唯一标识符：
        {
            'application': '',
            'session_id': '',
            'question_id': '',
            'request_id': ''
        }
    :param query_kwargs: 各来源检索的具体配置，支持baidu_kwargs, es_kwargs
    :param dedup_threshold: 去重的相似度阈值，来自difflib.SequenceMatcher(None, s1, s2).quick_ratio()。若threshold<=0则不去重。
    :param do_rank: 是否重排序，相似度来自BAAI/bge-base-zh，
    :param sim_threshold: 相似度阈值，0.65是一个试验过的默认值
    :param core_query: 相似的query
    :return: 结果dict
    """
    if query_kwargs is None:
        query_kwargs = {}
    iaar_database_kwargs = query_kwargs['iaar_database_kwargs'] if 'iaar_database_kwargs' in query_kwargs else None
    file_database_kwargs = query_kwargs['file_database_kwargs'] if 'file_database_kwargs' in query_kwargs else None

    err_msg = []
    all_result = {}

    # 多路搜索的回调函数
    def handle_result(result):
        (res, res_type, flag) = result
        if flag != 0:
            err_msg.append(res)
            return
        all_result[res_type] = res

    def query_function(search_type, raw_text, kwargs, topk=topk):
        if search_type == "SEARCH_TYPE_IAAR_DATABASE":
            return query_iaar_database(raw_text, kwargs, pro_flag)
        elif search_type == "SEARCH_TYPE_FILE_DATABASE":
            queries_embedding = query_embedding('test123', [raw_text])
            try:
                res = load_from_milvus(
                    queries_embedding, doc_id=kwargs.get('doc_id', []), topk=topk, user_id=user_info.get('user_id'),
                    mode=kwargs.get('pro_flag', True))
            except:
                res = []
                try:
                    if kwargs.get('pro_flag'):
                        print("error when load from milvus, try fast mode")
                        res = load_from_milvus(
                            queries_embedding, doc_id=kwargs.get('doc_id', []), topk=topk, user_id=user_info.get('user_id'),
                            mode=False)
                except:
                    traceback.print_exc()
            return res, search_type, 0

    with multiprocessing.Pool(processes=5) as pool:
        if iaar_database_kwargs:
            pool.apply_async(query_function, ("SEARCH_TYPE_IAAR_DATABASE", raw_text, iaar_database_kwargs), callback=handle_result)
        elif file_database_kwargs:
            pool.apply_async(query_function, ("SEARCH_TYPE_FILE_DATABASE", raw_text, file_database_kwargs), callback=handle_result)

        pool.close()
        pool.join()
    result = union_baidu_es_result(
        all_result.get("SEARCH_TYPE_IAAR_DATABASE", None),
        all_result.get("SEARCH_TYPE_FILE_DATABASE", None),
    )
    return result, err_msg


def rank_reference(query, contents, threshold=0.65):
    sim = get_sim_scores(query, contents)[0]
    sorted_ids = sorted(range(len(sim)), key=lambda k: sim[k], reverse=True)
    filtered_ids = []
    for id in sorted_ids:
        if sim[id] >= threshold:
            filtered_ids.append(id)
    return filtered_ids


def union_baidu_es_result(iaar_database_result, file_database_result):
    result = []
    if iaar_database_result:
        tmp_result = []
        for t in iaar_database_result:
            tmp = {
                "author": t['author'] if 'author' in t else '',
                "content": t['content'] if ('content' in t and t['content'] != '') else
                t['description'] if ('description' in t and t['description'] != '') else t.get('summary', ''),
                "images": t['images'] if 'images' in t else '',
                "images_url_list": t['images_url_list'] if 'images_url_list' in t else '',
                "publish_time": t['publish_time'] if 'publish_time' in t else '',
                "source": t['source'] if 'source' in t else '',
                "title": t['title'] if 'title' in t else '',
                "type": t['type'] if 'type' in t else '',
                "url": t['url'] if 'url' in t else '',
                "description": t['description'] if 'description' in t else t.get('summary', ''),
                "source_id": t['id'] if 'id' in t else '',
                "score": t['score'] if 'score' in t else '',
                'region': 'SEARCH_TYPE_IAAR_DATABASE',
                'otherinfo': ''
            }
            tmp_result.append(tmp)
        result += tmp_result
    if file_database_result:
        tmp_result = []
        for t in file_database_result:
            tmp = {
                "author": t['author'] if 'author' in t else '',
                "content": t['chunk'] if 'chunk' in t else '',
                "images": t['images'] if 'images' in t else '',
                "images_url_list": t['images_url_list'] if 'images_url_list' in t else '',
                "publish_time": t['publish_time'] if 'publish_time' in t else '',
                "source": t['source'] if 'source' in t else '',
                "title": t['title'] if 'title' in t else '',
                "type": t['type'] if 'type' in t else '',
                "url": t['url'] if 'url' in t else '',
                "description": t['chunk'] if 'chunk' in t else '',
                "source_id": t['doc_id'] if 'doc_id' in t else '',
                "oss_id": t['oss_id'] if 'oss_id' in t else '',
                "user_id": t['user_id'] if 'user_id' in t else '',
                "score": t['score'] if 'score' in t else '',
                'region': 'SEARCH_TYPE_FILE_DATABASE',
                'chunk_id': t['chunk_num'] if 'chunk_num' in t else '',
                'origin_content': t['origin_content'] if 'origin_content' in t else '',
                'chunk_poly': t['chunk_poly'] if 'chunk_poly' in t else '',
                'page_num': t['page_num'] if 'page_num' in t else '',
                'otherinfo': ''
            }
            tmp_result.append(tmp)
        result += tmp_result
    return result


def dedup_reference(contents, threshold=0.9):
    dup_ids = []
    for i in range(len(contents)):
        s1 = contents[i]
        for j in range(i + 1, len(contents)):
            s2 = contents[j]
            sim = difflib.SequenceMatcher(None, s1, s2).quick_ratio()
            if sim > threshold:
                dup_ids.append(j)
    return dup_ids


def process_highlights(highlighted_results, query_length):
    em_pattern = re.compile(r'<em>(.*?)<\/em>')
    processed_highlights = []
    for result in highlighted_results:
        highlighted_words = em_pattern.findall(result)
        if len(highlighted_words) >= 3 or any(len(word) >= 0.5 * query_length for word in highlighted_words):
            processed_highlights.append((result, len(highlighted_words)))
    return processed_highlights


def query_multi_source_preprocess(query_input: str, context, query_lib_dic: dict, query_kwargs: dict = {},
                                  sim_threshold: float = 0.55, dedup_threshold: float = 0.0, do_rank=False,
                                  core_query=None):
    final_refereces = []
    if len(query_input) < 38:
        query_abstract = query_input.strip()
    else:
        query_abstract = ' '.join(get_search_keywords(query_input))

    if "site" in query_input:
        if "net_kwargs" in query_kwargs:
            query_kwargs = {"net_kwargs": copy.deepcopy(query_kwargs["net_kwargs"])}
        else:
            return final_refereces, query_abstract, query_input

    if query_input == context.get_question() and "iaar_database_kwargs" in query_kwargs.keys():
        query_kwargs['iaar_database_kwargs']["online_search"]["bing_field"]["type"] = "page"

    res = query_all(
        context, query_input, query_kwargs=copy.deepcopy(query_kwargs), sim_threshold=sim_threshold,
        dedup_threshold=dedup_threshold, do_rank=do_rank,core_query=core_query
    )
    references = res[0]

    for reference in references:
        try:
            source = query_lib_dic[reference["region"]]
            # 百度检索
            if source == "net_kwargs":
                final_refereces.append({
                    "content": reference["content"],
                    "title": reference["title"],
                    "url": reference["url"],
                    "source": source,
                    "source_id": "",
                    "otherinfo": ""
                })
            # ES检索
            elif source == "doc_kwargs":
                final_refereces.append({
                    "content": reference["content"],
                    "title": reference["title"],
                    "url": reference["url"],
                    "source": source,
                    "source_id": reference["doc_id"],
                    "otherinfo": ""
                })
            #
            elif source == "credible_kwargs":
                final_refereces.append({
                    "content": reference["content"],
                    "title": reference["title"],
                    "url": reference["url"],
                    "source": source,
                    "source_id": "",
                    "otherinfo": ""
                })
            elif source == "summary_kwargs":
                final_refereces.append({
                    "content": reference["content"],
                    "title": reference["title"],
                    "url": "",
                    "source": source,
                    "source_id": reference["doc_id"],
                    "otherinfo": ""
                })
            elif source == "xinhua_kwargs":
                content = reference["textContent"] if (reference["textContent"] and reference["textContent"] != "") else \
                reference['content']
                content = remove_html_tags(content)
                final_refereces.append({
                    "content": content,
                    "title": reference['headLineRaw'] if
                    (reference["headLineRaw"] and reference["headLineRaw"] != "") else reference['title'],
                    "url": "",
                    "source": source,
                    "source_id": reference["doc_id"],
                    "otherinfo": ""
                })
            elif source in (SEARCH_TYPE_XINHUA_ES_MILVUS, "xinhua_vector_db_kwargs"):
                content = reference["content"]
                content = remove_html_tags(content)
                final_refereces.append({
                    "content": content,
                    "blockContent": reference["blockContent"],
                    "title": '',
                    "url": "",
                    "source": source,
                    "source_id": reference["id"],
                    "date": reference['chunkDateStr'],
                    "distance": reference['distance'],
                    "rerank_score": reference['rerank_score'],
                    "otherinfo": reference['otherinfo']
                })
            elif source in [SEARCH_TYPE_XINHUA_FAKE]:
                content = reference["content"]
                content = content
                final_refereces.append({
                    "content": content,
                    "blockContent": reference["blockContent"],
                    "title": '',
                    "url": "",
                    "source": source,
                    "source_id": reference["id"],
                    "date": reference['chunkDateStr'],
                    "distance": reference['distance'],
                    "rerank_score": reference['rerank_score'],
                    "otherinfo": reference['otherinfo']
                })
            elif source in [SEARCH_TYPE_XINHUA_INNER]:
                content = reference["content"]
                content = content
                final_refereces.append({
                    "content": content,
                    "blockContent": reference["blockContent"],
                    "title": '',
                    "url": "",
                    "source": source,
                    "source_id": reference["id"],
                    "date": reference['chunkDateStr'],
                    "distance": reference['distance'],
                    "rerank_score": reference['rerank_score'],
                    "otherinfo": reference['otherinfo']
                })
            elif source == SEARCH_TYPE_IAAR_DATABASE:
                #log.debug("reference:{}".format(reference))
                content = reference["content"]
                content = remove_html_tags(content)
                final_refereces.append({
                    "content": content,
                    "author": reference["author"],
                    "title": reference["title"],
                    "publish_time": reference["publish_time"],
                    "images": reference["images"],
                    "images_url_list": reference["images_url_list"],
                    "description": reference["description"],
                    "source": source,
                    "type": reference["type"],
                    "url": reference["url"],
                    "source_id": reference["source_id"],
                    "score": reference["score"],
                    "region": reference["region"],
                    "otherinfo": {"author": reference["author"],
                                  "title": reference["title"],
                                  "publish_time": reference["publish_time"],
                                  "images": reference["images"],
                                  "images_url_list": reference["images_url_list"],
                                  "description": reference["description"],
                                  "source": source,
                                  "type": reference["type"],
                                  "url": reference["url"],
                                  "source_id": reference["source_id"],
                                  "score": reference["score"],
                                  "region": reference["region"],
                                  "doc_id": reference["source_id"],
                                  "docId": reference["source_id"],
                                  "icon": reference["icon"] if 'icon' in reference else "",
                                  "all_content": reference["all_content"]}
                })



        except Exception as e:
            log.warning(e)
            log.info("source:{}".format(source))
            log.error("reference:{}".format(reference))
            import traceback
            traceback.print_exc()
            log.error("没有查到证据对应的来源库！跳过此条证据！")
    res_dict = final_refereces, query_abstract, query_input

    return res_dict

@trace_new(op="query_parallel_multi_source", logic_ep=True)
def query_parallel_multi_source(
        query_texts: list,
        query_lib_dic: dict,
        context,
        query_kwargs: dict,
        sim_threshold: float = 0.5,
        dedup_threshold: float = 0.0,
        do_rank=False
):
    """
    :param query_texts: 待查询文本
    :param query_kwargs: 请求的参数设置
    :return:
    """
    query_new = []
    for query in query_texts:
        if len(query) > 51:
            tmp = query[-50:]
            query_new.append(tmp)
        else:
            query_new.append(query)
    query_texts = query_new
    core_query = query_texts[0]
    log.warning("正在并行检索{}个query, 分别是：{}".format(len(query_texts), query_texts))
    # 开始做并发请求
    query_multi_source_partial_func = partial(
        query_multi_source_preprocess,
        context=context,
        query_lib_dic=query_lib_dic,
        query_kwargs=copy.deepcopy(query_kwargs),
        sim_threshold=sim_threshold,
        dedup_threshold=dedup_threshold,
        do_rank=do_rank,
        core_query=core_query
    )

    with ThreadPoolExecutor(max_workers=20) as executor:
        # map 函数将 query_multi_source_partial_func 应用到 query_texts 的每个元素
        res_all = list(executor.map(query_multi_source_partial_func, query_texts))

    return res_all

def top_n_indexes(lst, n):
    """计算topK的索引"""
    return sorted(range(len(lst)), key=lambda i: lst[i], reverse=True)[:n]

def query_xinhua_vector_fake(raw_text, body=None):
    '''通过网页的接口获取新华社检索结果'''
    # {
    #     "embeddingName": "embeddings_stella",      milvus
    #     "more_detail": "False",                     milvus
    #     "mediaTypeId": ["Photo"],                   milvus
    #     "required_keywords": ["国内考察", "习近平", ], es
    #     "optional_keywords": ["考察", "主席", "中国"], es

    #     "searchCategoryId": ["c210203001", "c2102"], es
    #     "start_time": "2023-01-01", es milvus
    #     "end_time": "2023-12-31",   es milvus
    #     "limit": "30", null
    # }
    url = "https://data.xinhua-news.cn/ChatSearch/time_block_search_2/"

    data = {"question": raw_text,
            "chatRecord": [],
            "referAnswer": "",
            "sourceString": "",
            "referContent": "",
            "userInfo": {"groupLeafPath": "iaar", "name": "tangbo"},
             "loc": "",
            "per": "",
            "level": "",
            "cid": "",
            "mediaTypeId": "",
            "userPrompt": "",
            "type": 1}

    if 'start_time' in body and len(body['start_time']) > 5:
        data['time'] = body['start_time'] + '/' + body['end_time']
    if 'optional_keywords' in body:
        data['keywordOne'] = ','.join(body['optional_keywords'])
    if 'required_keywords' in body:
        data['keywordAll'] = ','.join(body['required_keywords'])
    if 'searchCategoryId' in body:
        data['cid'] = ','.join(body['searchCategoryId'])
    if 'mediaTypeId' in body:
        data['mediaTypeId'] = body['mediaTypeId'][0]

    # 设置 POST 请求的头信息
    headers = {
        "Content-Type": "application/json"
    }

    # 发送 POST 请求
    res = None
    try:
        xinhuashe_response = requests.post(url, json=data, headers=headers)
        res = json.loads(xinhuashe_response.text)['time_blocks'][0]['time_block_items']
        #log.debug("xinhuashe_response:{}".format(res))
    except Exception as e:
        log.error("query_xinhua_vector_fake err:{}".format(e))

    return res, SEARCH_TYPE_XINHUA_FAKE, 0

def query_retrieval_es_service(data):
    """
        接口请求参数
        question string： 用户输入问题
    """
    # 发起POST请求
    res = requests.post(
        url="http://172.22.73.84:7676/search_full_content_es/",
        json=data,
        headers={
            "Accept": "application/json;charset=gb2312",
            "Content-Type": "application/json"}
    ).json()

    return json.dumps({
        "result": list(res['result'])
    }, ensure_ascii=False)

def query_retrieval_milvus_service(data):
    """
        接口请求参数
        question string： 用户输入问题
    """
    # 发起POST请求
    res = requests.post(
        url="http://172.22.73.84:7676/search_milvus2_multi/",
        json=data,
        headers={
            "Accept": "application/json;charset=gb2312",
            "Content-Type": "text/plain"},
        timeout=90
    ).json()

    return json.dumps({
        "result": list(res['result']['res'])
    }, ensure_ascii=False)

def query_retrieval_xhs_inner_service(data):
    """
        接口请求参数
        question string： 用户输入问题
    """
    # 发起POST请求
    res = requests.post(
        url = "http://172.22.73.84:7676/xhs_search/",
        json=data,
        headers={
            "Accept": "application/json;charset=gb2312",
            "Content-Type": "application/json"},
        timeout=90
    ).json()

    return json.dumps({
        "result": list(res['result']['res'])
    }, ensure_ascii=False)

if __name__ == "__main__":
    query = '习近平2024年两会行程'

    body = {
        "embeddingName": "embeddings_stella",
        "more_detail": "True",
        "required_keywords": [],
        "optional_keywords": [],
        #"searchCategoryId": ["c0030002", "c0050001", "c0030173", "c0090159"],
        "start_time": "2024-03-04",
        "end_time": "2024-03-11",
        #"mediaTypeId": ["Text"],
        "topk_es": "5000",
        "topk_vec": "500",
        "topk_rerank":"100",
        "limit": "10"
    }

    query = "今天有什么关于新能源的新闻？"
    body= {'search_type': ['online'],
           'online_search': {'max_entries': 20,
                             'topk_chunk': 30,
                             'baidu_field': {'switch': True, 'mode': 'relevance', 'type': 'page'},
                             'bing_field': {'switch': True, 'mode': 'relevance', 'type': 'page'},
                             'sogou_field': {'switch': False, 'mode': 'relevance', 'type': 'page'},
                             'start_date': '2024-06-21',
                             'end_date': '2024-06-21'},
           'queries': '今天有什么关于新能源的新闻？\n'}

    # useEs=True, rerank=True, LLMfilter=False,keyWordFilter=False
    # 模拟新华社
    #res2 = query_xinhua_vector_db_ES(query, body=body, useEs=False, rerank=False, LLMfilter=False, keyWordFilter=True)

    # 线上
    #res2 = query_xinhua_vector_db_ES(query, body=body, useEs=True, rerank=True, LLMfilter=False, keyWordFilter=False)

    # milvus + rerank
    #res2 = query_xinhua_vector_db_ES(query, body=body, useEs=False, rerank=True, LLMfilter=False, keyWordFilter=False)
    #res2 = query_xinhua_vector_inner(query, body_input=body)

    res2 = query_iaar_database(query, body_input=body)
    print(res2)

    # import pandas as pd
    # result = pd.DataFrame(res2)
    # result.to_excel('./saved.xlsx',index=False)


