import json
import requests
from elasticsearch import Elasticsearch
from typing import List, Union
from pymilvus import MilvusClient

from include.config import QueryReConfig 

es = Elasticsearch(QueryReConfig["QUERYRECDB"]["ES"]["url"],
                   http_auth=QueryReConfig["QUERYRECDB"]["ES"]["auth"])
mv_client = MilvusClient(
            uri=QueryReConfig["QUERYRECDB"]["MV"]["url"],
            user=QueryReConfig["QUERYRECDB"]["MV"]["auth"][0],
            password=QueryReConfig["QUERYRECDB"]["MV"]["auth"][1]
        )

class ESEgine(object):
    
    def __init__(self, configs=None) -> None:
        self.es = es

    def get_search(self, query, index_name, query_field="query.keyword", **kwargs):
        """
        query: str
        index_name: str
        query_field: str
        search_type: prefix, in, match, term
        """
        search_type = kwargs.get("search_type", "prefix")
        if search_type == "prefix":
            query_prefix = {
                "query": {
                    "prefix": {
                    query_field: {
                        "value": query
                    }}},
                "size": 200
            }
            results = self.es.search(index=index_name, body=query_prefix)
        elif search_type == "query_string":
            query_match = {
                "query": {
                    "query_string": {
                        "fields": [query_field.replace(".keyword", "")],
                        "query": query
                        }},
                    "size": 200
            }
            results = self.es.search(index=index_name, body=query_match)
        elif search_type == "match":
            query_match = {
                "query": {
                    "multi_match": {
                    "query": query,
                    "type": "most_fields",
                    "fields": [
                        query_field.replace(".keyword", "")
                    ]}},
                    "size": 200
            }
            results = self.es.search(index=index_name, body=query_match)
        elif search_type == "match_phrase":
            query_term = {
                "query": {
                    "match_phrase": {
                    query_field.replace(".keyword", ""): query
                    }
                 }
                }
            results = self.es.search(index=index_name, body=query_term)
        elif search_type == "match_phrase_slop":
            query_term = {
                "query": {
                    "match_phrase": {
                    query_field.replace(".keyword", ""): {
                        "query": query,
                        "slop":2
                    }
                    }
                 }
                }
            results = self.es.search(index=index_name, body=query_term)
        elif search_type == "match_phrase_slop_prefix":
            query_term = {
                "query": {
                    "bool": {
                    "should": [
                        {
                            "prefix": {  # 使用prefix查询提高相关性
                                query_field: {
                                    "value": query  # 假设我们基于第一个词做prefix匹配
                                }
                            }
                        },
                        {
                        "match_phrase": {
                            query_field.replace(".keyword", ""): {
                                "query": query,
                                "slop":2
                            }
                        }
                        }
                    ]
                    }
                }
                }
            results = self.es.search(index=index_name, body=query_term)
        elif search_type == "match_prefix":
            query_match = {
                "query": {
                    "bool": {
                    "should": [
                        {
                            "prefix": {  # 使用prefix查询提高相关性
                                query_field: {
                                    "value": query  # 假设我们基于第一个词做prefix匹配
                                }
                            }
                        },
                        {
                        "multi_match": {
                            "query": query,
                            "fields": [query_field.replace(".keyword", "")],
                            "type": "most_fields"
                        }
                        }
                    ]
                    }
                }
                }
            results = self.es.search(index=index_name, body=query_match)
        else:
            NotImplementedError
        return results
    
    def get_hot_search(self, index_name, query_field="query.keyword", **kwargs):
        human_label = kwargs.get("human_label", False)
        sorted_field = kwargs.get("sorted_field", "pub_time.keyword")
        if human_label:
            query = {
            "query": {
                "function_score": {
                "query": {
                    "match_all": {}
                    },
                 "functions":[
                             {
                    "filter": {
                        "term": {
                        query_field: "human"
                        }
                    },
                    "weight": 100
                    }],
                    "score_mode": "multiply",
                    "boost_mode": "multiply"}
                },
              "sort": [{
                    sorted_field: {
                        "order": "desc"}},
                    {
                    "_score": {
                        "order": "desc"
                    }
                    }
                ],
              "size": 200
            }
        else:
            query = {
                "query": {
                    "match_all": {}
                    },
              "sort": [
                    {
                    "hit_frequency": {
                        "order": "desc"
                        }
                    }
                ],
                "size": 200
            }
        results = self.es.search(index=index_name, body=query)
        return results
        

class MilvusEngine(object):

    def __init__(self, config=None) -> None:
        self.collection_name = "ainews_questions_test"
        self.client = mv_client

    def get_search(self, query: Union[List, str], query_field=None, **kwargs):
        """
        query:
        index_name:
        query_field: 
        """
        if type(query) == list:
            result = self.client.search(
                    collection_name=kwargs.get("collection_name","ainews_questions_test"), # Replace with the actual name of your collection
                    data=query, # Replace with your query vectors
                    limit=10, # Max. number of search results to return
                    output_fields=["hit_frequency","query_str", "event", "pub_time"]
                    #search_params={"metric_type": "AUTOINDEX", "params": {}} # Search parameters
            )
            return result
        else:
            raise NotImplementedError

def embeddings(batch_seq, url=None, token=None, model=None):
    if not token:
        token = QueryReConfig["QUERYRECDB"]["embedding"]["token"]
    if not model:
        model = QueryReConfig["QUERYRECDB"]["embedding"]["model"]
    if not url:
        url= QueryReConfig["QUERYRECDB"]["embedding"]["url"]
    payload = json.dumps({
    "model": model,
    "params": {
        "request_id": "autocomplete",
        "batch_seq": batch_seq
    }
    })
    headers = {
    'token': token,
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Host': '114.94.99.192:28034',
    'Connection': 'keep-alive'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return json.loads(response.text)


        
        
