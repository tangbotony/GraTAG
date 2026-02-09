import time
import json
from datetime import datetime
from typing import List, Tuple
from collections import OrderedDict, defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from include.utils.db_utils import embeddings
from include.utils import get_similarity


def time_decay_score(date_string, base_date=None, decay_factor=0.9) -> float:
    """
    计算时间衰减得分。
    
    参数:
    dates (list or pd.Series): 日期列表。
    base_date (datetime): 参照日期，默认为当前日期。
    decay_factor (float): 衰减因子，越接近1衰减越慢，越小则衰减越快。
    
    返回:
    pd.Series: 各日期对应的衰减得分。
    """
    if base_date is None:
        base_date = datetime.now()
    convert_time = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    # 将日期转换为与base_date的差值天数
    date_diffs = (base_date - convert_time).days # 转换为天数
    date_diffs = max(date_diffs / 7, 0.01)
    
    # 应用指数衰减公式计算得分
    scores = decay_factor ** date_diffs
    return scores

def calculate_score_byweight(results_mapping, weight)-> float:
    """
    results_mapping: {questions: quetions info}
    """
    score_info = defaultdict(float)
    for query, feature in results_mapping.items():
        for wtn, wts in weight.items():
            score_info[query] +=  feature[wtn] * wts
    sorted_score = sorted(score_info.items(), key=lambda item: item[1], reverse=True)
    return sorted_score

def calculate_diversity_by_embedding(query_list, top=50, timeout=1, threshold=0.95)-> List[Tuple]:
    """
    this function is make diverity for top
    """
    query_embeddings = embeddings(query_list[:top])
    similarity_matrix = cosine_similarity(query_embeddings).tolist()
    offset = 0
    final_query = []
    for index, scores in enumerate(similarity_matrix[offset:]):
        for score in scores[offset:]:
            if score < threshold:
                offset = index
                final_query.append((query_list[index], index))
                break
    return final_query

def calculate_diversity_by_field(step1_ranking, results_mapping, top=1, field="event")-> List[Tuple]:
    """
    this function is make diverity for top by speical field
    """
    filter_mapping  = defaultdict(int)
    final_query = []
    for index, query_info in enumerate(step1_ranking):
        if filter_mapping[results_mapping[query_info[0]][field]] < top:
            final_query.append(query_info)
            filter_mapping[results_mapping[query_info[0]][field]] +=1
    return final_query

def es_data_parse(data, field):
    """
    data: es data
    field: mapping key
    """
    results_mapping = OrderedDict()
    for hit in data["hits"]["hits"][:100]:
        if hit["_source"][field]  in results_mapping:
            continue
        results_mapping[hit["_source"][field]] = {"score":hit["_score"], 
                                                    "hit_frequency":hit["_source"]["hit_frequency"], 
                                                    "pub_time": time_decay_score(hit["_source"]["pub_time"]),
                                                    "event": hit["_source"]["event"],
                                                    "pub_time_format": hit["_source"]["pub_time"],
                                                    "question_type": hit["_source"]["question_type"],
                                                    "news_category": hit["_source"]["news_category"]
                                                    }
    return results_mapping

def embed_data_parse(data, field, recall_threshold=0.85):
    """
    data: es data
    field: mapping key
    """
    results_mapping = OrderedDict()
    for hit in data[0][:100]:
        if hit["entity"][field]  in results_mapping:
            continue
        if hit["distance"] < recall_threshold:
            continue
        results_mapping[hit["entity"][field]] = {"score":hit["distance"], 
                                                    "hit_frequency":hit["entity"]["hit_frequency"], 
                                                    "pub_time": time_decay_score(hit["entity"]["pub_time"]),
                                                    "event": hit["entity"]["event"],
                                                    "pub_time_org": hit["entity"]["pub_time"],
                                                    "question_type": hit["entity"]["question_type"],
                                                    "news_category": hit["entity"]["news_category"]
                                                    }
    return results_mapping

def get_diversity(step1_ranking, results_mapping, diversity_ranking)-> List[Tuple]:
    if not diversity_ranking:
        return step1_ranking[:10]
    elif diversity_ranking == "field":
        return calculate_diversity_by_field(step1_ranking=step1_ranking, results_mapping=results_mapping)[:10]
    else:
        return calculate_diversity_by_embedding(query_list=[query[0] for query in step1_ranking], top=10, threshold=0.8)
    
def get_similarity_score(query: str,results_mapping:Tuple, similarity_threshold: float, return_all:bool=False)-> Tuple:
    """
    caculate similarity
    """
    str_list2 = [k for k, v in results_mapping.items()]
    score_list = get_similarity(str_list1=[query], str_list2=str_list2)
    for index, question in enumerate(str_list2):
        if score_list[0][index]< similarity_threshold:
             results_mapping.pop(question)
        elif query and len(query) <= 3:
            for cha in query:
                if cha not in question:
                    results_mapping.pop(question)
                    break
        else:
            if return_all:
                results_mapping[question]["score"] = score_list[0][index]
            else:
                results_mapping[question]["score"] = score_list[0][index] if score_list[0][index]> 0.6 else -100
    return results_mapping

def dynamic_similarity_threshold(query, min_threshold=0.4, max_threshold=0.95, max_length=20):
    """
    根据query的长度线性计算相似度阈值。
    
    :param query: 用户输入的查询字符串
    :param min_threshold: 最小相似度阈值
    :param max_threshold: 最大相似度阈值
    :param max_length: 达到最大相似度阈值的查询长度
    :return: 计算出的动态相似度阈值
    """
    length = len(query)
    
    # 通过线性插值计算当前长度对应的阈值
    if length >= max_length:
        return max_threshold
    
    # 计算动态阈值
    dynamic_threshold = min_threshold + (max_threshold - min_threshold) * (length / max_length)
    return dynamic_threshold


def get_ranking_reuslts(data:List, query:str=None,return_all=False, **kwargs)-> List[Tuple]:
    """
    参数:
        ranking_weight: 重排序的权重
        field : 召回字段
        use_channel: 召回数据通道
        diversity_ranking: 多样性去重的方法embedding, field日期采样
    """
    ranking_weight = kwargs.get("ranking_weight")
    field = kwargs.get("field", "query")
    use_channel = kwargs.get("use_channel", "es")# es, mulvis, multi
    diversity_ranking = kwargs.get("diversity_ranking", "field")
    similarity_threshold = kwargs.get("similarity_threshold", 0.4)
    step1_ranking = None
    results_mapping = None
    if use_channel == "es":
        results_mapping = es_data_parse(data, field)

    elif use_channel == "embedding":
        results_mapping = embed_data_parse(data, field="query_str" if field=="query" else field)
    else:
        results_mapping_es = es_data_parse(data[0], field)
        results_mapping_embed = embed_data_parse(data[1], field="query_str" if field=="query" else field)
        for k, v in results_mapping_embed.items():
            if k not in results_mapping_es:
                results_mapping_es.update({k: v})
        results_mapping = results_mapping_es
    if ranking_weight["score"] > 0 and query:
        if return_all:
            "返回所有事件信息"
            results_mapping = get_similarity_score(query, results_mapping, similarity_threshold=0.1, return_all=return_all)
            final_results = sorted(results_mapping.items(), key=lambda item: item[1]['score'], reverse=True)
            return final_results
        dynamic_threshold = dynamic_similarity_threshold(query=query, min_threshold=similarity_threshold)
        results_mapping = get_similarity_score(query, results_mapping, dynamic_threshold)
    step1_ranking = calculate_score_byweight(results_mapping, ranking_weight)
    final_results = get_diversity(step1_ranking, results_mapping, diversity_ranking)
    return final_results