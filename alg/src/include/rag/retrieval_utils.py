import re
import json
import requests
import traceback
from include.logger import log
from include.config import CommonConfig
from include.config import PromptConfig, RagQAConfig
from include.utils.llm_caller_utils import llm_call
from concurrent.futures import ThreadPoolExecutor
import time

def similarity_util_text_filter(input_str):
    """
    使用正则表达式匹配汉字、英文和数字，并且去掉其他字符
    :param input_str:
    :return:
    """
    result = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。？！；：“”‘’（）{}《》, .?!;:\"\']', '', input_str)
    return result


def repeat(input1, input2, repeat_type):
    # TODO
    raise NotImplementedError

    def get_clean_repetition_sentence(content):
        sep_lines = sep_text_by_line_for_check(content)
        vec_sim = get_similarity(sep_lines, sep_lines)
        need_to_del_line = set()
        for i in range(len(sep_lines)):
            for j in range(i + 1, len(sep_lines)):
                if vec_sim[i][j] > 0.95:
                    # print(f"句子 '{sep_lines[i]}' 和句子 '{sep_lines[j]} 的相似度为{vec_sim[i][j]}")
                    need_to_del_line.add(j)
        for need_del in need_to_del_line:
            log.warning("待删除的句子: " + sep_lines[need_del])

        final_ans = ""
        for index in range(len(sep_lines)):
            if index not in need_to_del_line:
                final_ans += sep_lines[index]
        return final_ans.replace("SEP_PARA", "\n\n")

    def is_self_repeat(current_batch):
        '''
        判断当前生成的一组论点是否自相重复
        '''
        invalid = False
        for i in range(len(current_batch) - 1):
            curr_opinion = current_batch[i]
            comp_opinion_list = current_batch[i + 1:]
            curr_score = get_similarity([curr_opinion], comp_opinion_list)[0]
            if max(curr_score) > 0.97:
                invalid = True
                log.info("当前论点自重复！")
                break
        return invalid

    def is_former_repeat(current_batch, generated_sub_opinion_list):
        '''
        判断当前补充生成的论点是否跟已有前置论点重复
        '''
        invalid = False
        comp_opinion_list = generated_sub_opinion_list
        for i in range(len(current_batch)):
            curr_opinion = current_batch[i]
            curr_score = get_similarity([curr_opinion], comp_opinion_list)[0]
            if max(curr_score) > 0.97:
                invalid = True
                log.info("当前生成论点与之前生成论点重复！")
                break
        return invalid

    def is_his_repeat(current_batch, current_page_idx, his_opinion_dict):
        '''
            判断当前轮次生成论点是否跟历史生成论点重复
        '''
        invalid = False
        his_opinion_list = []
        for page_idx, his_page_subopinion in his_opinion_dict.items():
            if page_idx == current_page_idx:
                continue
            for subopinion_dict in his_page_subopinion.values():
                if "opinion" in subopinion_dict and len(subopinion_dict["opinion"]) > 0:
                    his_opinion_list.append(subopinion_dict["opinion"])
        if len(his_opinion_list) > 0:
            log.info("历史论点：{}".format(his_opinion_list))
            comp_opinion_list = his_opinion_list
            sim_score_list = get_similarity(current_batch, comp_opinion_list)
            sim_cnt = 0
            for i in range(len(current_batch)):
                if max(sim_score_list[i]) > 0.95:
                    sim_cnt += 1
            if sim_cnt / len(current_batch) >= 0.5:
                log.info("当前论点与历史论点重复！")
                invalid = True
        else:
            log.info("没有历史论点，跳过历史论点重复性判断。")
        return invalid

    def invalid_rouge_score(major_opinion, sub_opinion_list):
        '''
        利用rouge指标计算生成子论点是否和由头内容重复
        '''
        invalid = False
        rouge = Rouge()
        for sub_opinion in sub_opinion_list:
            scores = rouge.get_scores(" ".join(list(major_opinion)), " ".join(list(sub_opinion)))
            result = scores[0]
            print(result)
            if result['rouge-l']['r'] > 0.9:
                log.info("当前论点与由头重复度过高，重新生成：" + str(sub_opinion))
                invalid = True
                break
        return invalid


def edit_distance(s1, s2):
    n = len(s1)
    m = len(s2)

    dp = [[0 for _ in range(m + 1)] for _ in range(n + 1)]
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            # print(dp)
            if i == n:
                dp[i][j] = m - j
            elif j == m:
                dp[i][j] = n - i
            else:
                d1 = 1 + dp[i + 1][j]
                d2 = 1 + dp[i][j + 1]
                d3 = dp[i + 1][j + 1] if s1[i] == s2[j] else 1 + dp[i + 1][j + 1]
                dp[i][j] = min(d1, d2, d3)
    return dp[0][0]


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
            response = requests.request("POST", url, headers=headers, json=payload, timeout=30)
            return json.loads(response.text)['response']
        except Exception as e:
            log.warning(e)
            log.warning(traceback.print_exc())
            str_list1 = [similarity_util_text_filter(text1_i) for text1_i in str_list1]
            str_list2 = [similarity_util_text_filter(text2_i) for text2_i in str_list2]
            num_try += 1
            if num_try > 5:
                m, n = len(str_list1), len(str_list2)
                return [[0.5 for _ in range(n)] for _ in range(m)]
            continue
    return []


def rerankBge(query: str, docList: list, config=CommonConfig, rerankModel=None):
    num_try = 0
    if len(docList) == 0:
        return []
    while True:
        try:
            url = config['url']
            headers = {
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'token':"xxx"
            }
            payload = {
                "model": "BAAI_bge_reranker_v2_m3_infinity",
                "params": {
                    "request_id": "123",
                    "query": query,
                    "docs": docList
                },
                "return_documents": False
            }
            response = requests.request("POST", url, headers=headers, json=payload, timeout=30)
            score_list = json.loads(response.text)['response']
            # for score_dict in json.loads(response.text)['response']:
            #     score_list.append(score_dict['relevance_score'])
            return score_list

        except Exception as e:
            log.warning(e)
            num_try += 1
            if num_try > 5:
                log.error(e)
                return None
            continue
    return None


def batchQueryDocCorrelation(str_list1: list, str_list2: list):
    str_list1 = [str_i if 1 <= len(str_i) <= 1000 else " " for str_i in str_list1]
    str_list2 = [str_i if 1 <= len(str_i) <= 1000 else " " for str_i in str_list2]

    m, n = len(str_list1), len(str_list2)
    ans0 = [[0.5 for _ in range(n)] for _ in range(m)]

    pairs = []
    for str1 in str_list1:
        for str2 in str_list2:
            pairs.append([str1, str2])

    # 创建ThreadPoolExecutor对象
    with ThreadPoolExecutor(max_workers=12) as executor:
        # 提交任务
        futures = [executor.submit(queryDocCorrelation, pair[0], pair[1]) for pair in pairs]

        # 获取任务执行结果
        results = [future.result() for future in futures]

    ll = len(str_list2)
    chunked_list = [results[i:i + ll] for i in range(0, len(results), ll)]
    # print(chunked_list)

    return chunked_list


def batchQueryDocCorrelationSeq(str_list1: list, str_list2: list):
    str_list1 = [str_i if 1 <= len(str_i) <= 1000 else " " for str_i in str_list1]
    str_list2 = [str_i if 1 <= len(str_i) <= 1000 else " " for str_i in str_list2]

    pairs = []
    for idx, str1 in enumerate(str_list1):
        str2 = str_list2[idx]
        pairs.append([str1, str2])

    # 创建ThreadPoolExecutor对象
    with ThreadPoolExecutor(max_workers=12) as executor:
        # 提交任务
        futures = [executor.submit(queryDocCorrelation, pair[0], pair[1]) for pair in pairs]

        # 获取任务执行结果
        results = [future.result() for future in futures]

    return None, results


def find_best_unrelated_subgroup(sentences: list, similarity_matrix: list, bar: float = 0.8):
    assert len(sentences) == len(similarity_matrix), "最大独立集时，输入的句子和相似度矩阵维度有误"

    num_sentence = len(sentences)
    # 初始化
    selected_sentences = []
    selected_indices = []

    # 贪心算法
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

    headers = {
        "token": config['AUTH_CONFIG']['key'],
    }

    url = config['FSCHAT']["general_url"]
    res_temp = requests.request("POST", url, headers=headers, json=payload, timeout=20)
    return eval(res_temp.content)


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

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        log.info(f"函数 {func.__name__} 的执行时间为：{elapsed_time}秒")
        return result
    return wrapper

if __name__ == '__main__':
    import numpy as np

    # res = get_similarity(["北京", "上海"], ["纽约", "北京"])
    # res = np.array(res).squeeze(axis=1)
    # filter = np.all(np.logical_or(res < 0.63, res > 0.9))
    # print(res)
    # res2 = get_embeddings("lalalalalalalallala")
    # print(res2)

    query = '今年两会，北京代表团的代表们有哪些主要的政治诉求或关注点？'
    doc = '（“两会”倒计时） 又是三月进京来 基层代表关心啥？ （“两会”倒计时） 又是三月进京来 基层代表 关心啥？'
    tmp = queryDocCorrelation(query, doc)
    print(tmp)

    query = '今年两会政府工作报告中关于促消费的举措有哪些？'
    doc = '促进消费稳定增长。从增加收入、优化供给、减少限制性措施等方面综合施策，激发消费潜能。培育壮大新型消费，实施数字消费、绿色消费、健康消费促进政策，积极培育智能家居、文娱旅游、体育赛事、国货“潮品”等新的消费增长点。稳定和扩大传统消费，鼓励和推动消费品以旧换新，提振智能网联新能源汽车、电子产品等大宗消费。推动养老、育幼、家政等服务扩容提质，支持社会力量提供社区服务。优化消费环境，开展“消费促进年”活动，实施“放心消费行动”，加强消费者权益保护，落实带薪休假制度。实施标准提升行动，加快构建适应高质量发展要求的标准体系，推动商品和服务质量不断提高，更好满足人民群众改善生活需要。'
    tmp = queryDocCorrelation(query, doc)
    print(tmp)
