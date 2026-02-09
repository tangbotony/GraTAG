import re
from typing import List, Tuple, Dict
from include.utils.db_utils import embeddings
from include.utils.similarity_utils import similarity_util_text_filter


def recall_processing(query):
    replaced_string = re.sub(r'\[|\]', '', query)
    return replaced_string

def get_recall_results(data, use_channel="es", es_engine=None, mv_engine=None, **kwargs) -> Dict:
    """获取query推荐的recall"""
    query = data["query"]
    query = similarity_util_text_filter(query)
    query = recall_processing(query)
    if use_channel == "es":
        return es_engine.get_search(query=query, **kwargs)
    elif use_channel == "embedding":
            query_embedding = embeddings([query])
            return mv_engine.get_search(query_embedding, **kwargs)
    else:
        es_results = es_engine.get_search(query=query, **kwargs)
        query_embedding = embeddings([query])
        embed_results = mv_engine.get_search(query_embedding, **kwargs)
        return es_results, embed_results
    
def get_hotrecall_results(data=None, use_channel="es", es_engine=None, mv_engine=None, **kwargs) -> Dict:
    """获取主页热门推荐的recall"""
    if use_channel == "es":
        index_name= kwargs.pop("index_name")
        return es_engine.get_hot_search(index_name=index_name, **kwargs)