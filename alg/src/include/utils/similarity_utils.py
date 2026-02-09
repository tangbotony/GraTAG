import re
import json
import requests
import traceback
from datasketch import MinHash, MinHashLSH
from nltk import ngrams
from include.logger import log
from include.config import CommonConfig
from include.config import PromptConfig, RagQAConfig
from include.utils.llm_caller_utils import llm_call


def similarity_util_text_filter(input_str):
    """
    use regex to match Chinese, English and number characters, and delete any other characters
    :param input_str:
    :return:
    """
    result = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。？！；：“”‘’（）{}《》, .?!;:\"\']', '', input_str)
    return result

def get_similarity(str_list1: list, str_list2: list, request_id="", config=CommonConfig):
    str_list1 = [str_i if 1 <= len(str_i) <= 1000 else " " for str_i in str_list1]
    str_list2 = [str_i if 1 <= len(str_i) <= 1000 else " " for str_i in str_list2]
    num_try = 0
    url = config["SIMILARITY_CONFIG"]["url"]
    while True:
        try:
            payload = {
                "model": config["SIMILARITY_CONFIG"]["baai_sim_general"],
                "params": {
                    "request_id": request_id,
                    "text_a": str_list1,
                    "text_b": str_list2
                }
            }
            headers = {
                "token": config["AUTH_CONFIG"]["key"],
            }
            response = requests.request("POST", url, headers=headers, json=payload, timeout=5)
            return json.loads(response.text)['response']
        except Exception as e:
            log.warning(e)
            log.warning(traceback.print_exc())
            str_list1 = [similarity_util_text_filter(text1_i) for text1_i in str_list1]
            str_list2 = [similarity_util_text_filter(text2_i) for text2_i in str_list2]
            num_try += 1
            if num_try > 2:
                m, n = len(str_list1), len(str_list2)
                return [[0.5 for _ in range(n)] for _ in range(m)]
            continue
    return []


def find_best_unrelated_subgroup(sentences: list, similarity_matrix: list, bar: float = 0.8):
    assert len(sentences) == len(similarity_matrix), "最大独立集时，输入的句子和相似度矩阵维度有误"

    num_sentence = len(sentences)
    selected_sentences = []
    selected_indices = []

    for i in range(num_sentence):
        can_add = True
        for j in selected_indices:
            if similarity_matrix[i][j] > bar:
                can_add = False
                break
        if can_add:
            selected_sentences.append(i)
            selected_indices.append(i)
    return selected_sentences, selected_indices


def get_embeddings(text_list, request_id=0, config=CommonConfig):
    payload = {
        "model": config['SIMILARITY_CONFIG']["embedding"],
        "params": {
            "request_id": request_id,
            "batch_seq": text_list
        }
    }

    headers = {"token": config['AUTH_CONFIG']['key']}


    url = config["SIMILARITY_CONFIG"]["url"]
    res_temp = requests.request("POST", url, headers=headers, json=payload, timeout=20)
    return eval(res_temp.content)

def get_chunk_embeddings(input_text:list, request_id , chunk_size = 350, overlap = 85, chunk_max_size = 2000):
    model = CommonConfig['CHUNK_SPLIT']['model']
    url = CommonConfig['FSCHAT']['general_url']

    payload = json.dumps({
        "model": model,
        "params": {
            "request_id": request_id,
            "batch_seq": input_text,
            "text_splitter_config": {
                "splitter_type": "Recursive",
                "only_splitter": False,
                "Recursive": {
                    "chunk_size": chunk_size,
                    "chunk_overlap": int(overlap),
                    "chunk_max_size": chunk_max_size
                },
            }
        }
    })


    headers = {
        'token': CommonConfig['AUTH_CONFIG']['key'],
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    # headers = {"token": CommonConfig['AUTH_CONFIG']['key']}
    response = requests.request("POST", url, headers=headers, data=payload, timeout=120)
    results = json.loads(response.text)
    return results
    

def edit_distance(s1, s2):
    n = len(s1)
    m = len(s2)
    
    dp = [[0 for _ in range(m+1)] for _ in range(n+1)]
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            # print(dp)
            if i == n:
                dp[i][j] = m-j
            elif j == m:
                dp[i][j] = n-i
            else:
                d1 = 1 + dp[i+1][j]
                d2 = 1 + dp[i][j+1]
                d3 = dp[i+1][j+1] if s1[i] == s2[j] else 1 + dp[i+1][j+1]
                dp[i][j] = min(d1, d2, d3)
    return dp[0][0]


def check_stepback(text1, text2, clip = [0.6, 0.85]):
    """
    注意输入text为中文时，以string形式传入
    输入text为英文时，以list形式传入
    """
    # step1:
    edit_dis = edit_distance(text1, text2)
    if  0.1 < (edit_dis/len(text1)) < 0.9:
        pass 
    else:
        return False
    # step2
    low_threhold, hight_threhold= clip
    res = get_similarity([text1], [text2])[0][0]
    if not res:
        return False
    res = float(res)
    if low_threhold < res < hight_threhold:
        return True 
    else:
        return False

def minhash_filter_repeat(queries, gram = 5, perm = 128, k = 0.8, return_bool = False):
    """
    通过minhash做去重
    :param queries: query 的列表
    :param 其他参数是阈值，不用修改
    :return List[str] 返回保留的query
    """
    if queries == []:
        return queries
    lsh = MinHashLSH(threshold=k, num_perm=perm)
    filter_record = []
    keep_record = []
    for idx, query in enumerate(queries):
        minhash = MinHash(num_perm=perm)
        for d in ngrams(query, gram):
            minhash.update("".join(d).encode('utf-8'))
        lsh.insert(idx, minhash)
        similiar_group = lsh.query(minhash)
        if len(similiar_group) >1:
            filter_record.append(False)
        else:
            filter_record.append(True)
            keep_record.append(query)
    if return_bool:
        return filter_record
    else:
        return keep_record


def queryDocCorrelation(query, doc, model_name=None):
    '''
    判断query与材料是否有关联
    :param query: 查询query
    :param doc: 文档
    :return: True False bool
    '''
    model_name = RagQAConfig["TASK_MODEL_CONFIG"]["queryDocCorr"]
    task_name = PromptConfig["queryDocCorrelation"]["task_desc"]
    task_prompt_template = PromptConfig["queryDocCorrelation"]["instruction"]
    prompt = task_prompt_template.format(query, doc)

    ans = False
    retry_cnt = 0
    max_try_cnt = 5
    while True:
        try:
            response = llm_call(prompt, model_name, task_name=task_name)
            if 'true' in response or 'True' in response:
                ans = True
            break
        except Exception as e:
            log.warning(
                "queryDocCorrelation occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(),
                                                                                                retry_cnt,
                                                                                                max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                log.warning(
                    "queryDocCorrelation occurs error: {}, retry cnt:{}/{}, return None.".format(e, retry_cnt,
                                                                                                     max_try_cnt))
                break
    return ans


def similarity_filter_list(queries, threshold = 0.6):
    if queries == []:
        return queries
    similarity_score = get_similarity(queries, queries)
    keep_queries = [queries[0]]
    for i in range(1, len(similarity_score)):
        flag = True
        for j in range(i):
            if similarity_score[i][j] > threshold:
                flag = False 
                break 
        if flag:
            keep_queries.append(queries[i])

    return keep_queries



if __name__ == '__main__':
    import time
    queries = ["如何通过良好的生活习惯有效保持身材？", "维持理想身材的全面健康生活习惯包括哪些方面？"]
    # queries = ['斯洛伐克总理遇刺事件的起因是什么？', '斯洛伐克总理遇刺事件是如何得到解决的，以及这一事件对斯洛伐克政治格局产生了哪些影响？', '斯洛伐克总理遇刺事件具体发生在什么时间？']
    st = time.time()
    res = minhash_filter_repeat(queries)
    print(res, time.time() - st)

    st = time.time()
    res = get_similarity(queries, queries)
    print(res, time.time() - st)