import json
from include.logger import log
from elasticsearch import Elasticsearch
from include.config import CommonConfig


def save_to_es(data, session_id, es_name="ES_QA", index_name="ai_news_qa"):
    es_write = {
        "session_id": session_id,
        'data': json.dumps(data)
    }
    es = Elasticsearch(hosts=CommonConfig[es_name]['url'], http_auth=('elastic', CommonConfig[es_name]['elastic']))

    # Check if a document with the same session_id already exists
    response = es.exists(index=index_name, id=session_id)
    if response:
        # If it exists, delete the document
        es.delete(index=index_name, id=session_id)
        es.indices.refresh(index=index_name)
    es.index(index=index_name, id=session_id, body=es_write)
    es.indices.refresh(index=index_name)


def load_from_es(es_query, es_name="ES_QA", index_name="ai_news_qa"):
    try:
        es = Elasticsearch(hosts=CommonConfig[es_name]['url'], http_auth=('elastic', CommonConfig[es_name]['elastic']))
        search_results = es.search(index=index_name, body=es_query)  
        if search_results['hits']['total']['value'] > 0:
            assert len(search_results['hits']['hits']) == 1, "ES中目标数据不唯一！"
            data = json.loads(search_results['hits']['hits'][0]['_source']['data'])
            return data
        else:
            return None
    except:
        log.warning("File not found!")
        return None


if __name__ == '__main__':
    data = {"key": "你好吗吗吗"}
    save_to_es(data, 456711, es_name="ES_QA", index_name="default")
    data = load_from_es({
        "query": {
            "bool": {
                "must": [
                    {"match": {"session_id": 456711}}
                ]
            }
        },
        "size": 10  # Limit the number of returned documents to 1000
    }, es_name="ES_QA", index_name="default")
    print(data)