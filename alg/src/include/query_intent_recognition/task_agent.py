import time

import datetime
import traceback
import copy
from multiprocessing.dummy import Pool as ThreadPool

from concurrent.futures import ThreadPoolExecutor
import json
import requests
import tqdm

from include.decorator import timer_decorator
from include.logger import log
from include.utils.llm_caller_utils import llm_call
from include.utils.similarity_utils import get_similarity
from include.utils.text_utils import calculate_english_ratio
from include.config import PromptConfig, QueryIRConfig, QueryReConfig
from include.utils.db_utils import ESEgine, MilvusEngine
from include.query.query_recall import get_recall_results
from include.query.query_ranking import get_ranking_reuslts
from include.utils.skywalking_utils import trace_new, start_sw


@trace_new(op="get_reject_judgement")
@timer_decorator
def get_reject_judgement(init_question, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["query_reject"], clogger=log):
    '''
    对用户输入问题进行拒答判断
    :return: reject_judgement:  {"is_reject":True/False, "rejectreason":"xx"}
    '''
    task_prompt_template = PromptConfig["query_reject"]["instruction"]
    query = task_prompt_template.format(init_question)
    # clogger.info(query)
    reject_judgement = {"is_reject": False}  # 兜底范围返回不做拒答
    retry_cnt = 0
    max_try_cnt = 5  # {"是否拒答":"否"}
    while True:
        try:
            response = llm_call(query=query, model_name=model_name, temperature=0.0,
                                task_name=PromptConfig["query_reject"]["task_desc"],
                                clogger=clogger)
            response = eval(response.replace("```json\n", "").replace("\n```", ""))
            # clogger.info("success getting raw refuse_judgement result: {}".format(response))
            assert isinstance(response, dict), "模型输出格式不符合预期"
            if response.get('是否拒答', "") != "":
                if response['是否拒答'] == '是':
                    if response.get('问题类别', "") == "高等数学及编程类问题":
                        # 只对高等数学及编程类问题进行拒答
                        reject_judgement = {"is_reject": True, "reject_reason": '高等数学及编程类问题'}
                    else:
                        reject_judgement = {"is_reject": False, "reject_reason": response.get('问题类别', "")}
                    break
                else:
                    reject_judgement = {"is_reject": False}
                    break
        except Exception as e:
            clogger.warning(
                "get_reject_judgement occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(),
                                                                                             retry_cnt,
                                                                                             max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                clogger.warning(
                    "get_reject_judgement occurs error: {}, retry cnt:{}/{}, return {}.".format(e, retry_cnt,
                                                                                                max_try_cnt,
                                                                                                reject_judgement))
                break
    return reject_judgement


@trace_new(op="get_question_supplement")
@timer_decorator
def get_question_supplement(init_question, query_time='',
                            model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["query_supplement"], clogger=log):
    '''
    分析用户输入问题的具体性与明确性，判断是否需要用户进行问题补充确认，如有需要，识别需补充的关键信息并构造补充选项
    :param init_question: 用户输入原始问题
    :param query_time: 用户提问时间背景 "%Y年%m月%d日"
    :return: question_supplement:  {}/{"description":"xx","choices":["xx", "xx", ....]}
    '''
    task_prompt_template = PromptConfig["query_supply"]["instruction"]
    if query_time == '':
        query_time = time.strftime("%Y年%m月%d日", time.localtime())
    query = task_prompt_template.format(query_time, init_question)
    # clogger.info(query)
    question_supplement = {"is_supply": False}  # 兜底结果为不需要进行问题补充
    retry_cnt = 0
    max_try_cnt = 8
    while True:
        try:
            response = llm_call(query=query, model_name=model_name, temperature=0.0,
                                task_name=PromptConfig["query_supply"]["task_desc"],
                                clogger=clogger)
            response = eval(response.replace("```json\n", "").replace("\n```", ""))
            # clogger.info("success getting raw question_supplement result: {}".format(response))
            assert isinstance(response, dict)
            if response.get('是否需要补充', "") != "":
                if response['是否需要补充'] == '否':
                    question_supplement = {"is_supply": False}
                    break
                elif response['是否需要补充'] == '是' and isinstance(response.get('补充选项', ""), dict):
                    try:
                        supplement_info = response['补充选项']
                        if supplement_info.get('补充描述', "") != "" and isinstance(supplement_info.get("选项内容", ""),
                                                                                    list):
                            supply_choices = supplement_info["选项内容"][:5]
                            if ("A" in supply_choices[0] and "B" in supply_choices[0]) or (
                                    "1" in supply_choices[0] and "2" in supply_choices[0]):
                                question_supplement = {"is_supply": False}
                            else:
                                question_supplement = {"is_supply": True,
                                                       "supply_description": supplement_info['补充描述'],
                                                       "supply_choices": supply_choices}
                            break
                    except:
                        question_supplement = {"is_supply": False}
                        break
        except Exception as e:
            clogger.warning(
                "get_question_supplement occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(),
                                                                                                retry_cnt,
                                                                                                max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                clogger.warning(
                    "get_question_supplement occurs error: {}, retry cnt:{}/{}, return {}.".format(e, retry_cnt,
                                                                                                   max_try_cnt,
                                                                                                   question_supplement))
                break
    return question_supplement


@trace_new(op="get_reinforced_qkw")
@timer_decorator
def get_reinforced_qkw(question, need_keyword=False, query_time='', query_supplement=None, clogger=log):
    '''
    基于原问题、补全问题信息(如有)进行问题增强，生成 "内容掌握"、"要素了解"、"脉络梳理"、"扩展思考" 4个维度的增强问题，并对增强后问题提取关键词
    :param question: 用户输入原始问题
    :param query_time: 用户提问时间背景
    :param query_supplement: 补全问题信息 {}/{"description":"xx","choices":["xx", "xx", ....]}
    :return: reinforced_qkw: list[dict] 问题字典列表 [{"question":"xx","keywords":["xx","xx",....],"question_type":""}]
    '''
    if query_supplement is None:
        query_supplement = {}
    reinforced_question_dict = get_reinforced_questions(question, query_time=query_time,
                                                        query_supplement=query_supplement, clogger=clogger)
    if reinforced_question_dict is None or reinforced_question_dict == {}:
        return None
    if need_keyword:
        reinforced_qkw = get_reinforced_questions_keywords(reinforced_question_dict, clogger=clogger)
        return reinforced_qkw
    else:
        reinforced_question_list = []
        for q_type, q_list in reinforced_question_dict.items():
            for q in q_list:
                reinforced_question_list.append({"question": q, "question_type": q_type})
        return reinforced_question_list


@trace_new(op="get_reinforced_questions")
def get_reinforced_questions(question, query_time='', query_supplement=None,
                             model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["query_reinforce"], clogger=log):
    '''
    基于原问题、补全问题信息(如有)进行问题增强，生成 "内容掌握"、"要素了解"、"脉络梳理"、"扩展思考" 4个维度的增强问题
    :param question: 用户输入原始问题
    :param query_time: 用户提问时间背景
    :param query_supplement: 用户确认补全问题信息 {}/{"description":"xx","choices":["xx", "xx", ....]}
    :return: reinforced_question_dict: dict[str,list] 问题字典列表 {"内容掌握":["xx","xx",....],"要素了解":["xx","xx",....],...]
    '''
    task_prompt_template = PromptConfig["quick_query_reinforce"]["instruction"]
    if query_time is None or query_time == '':
        query_time = time.strftime("%Y年%m月%d日", time.localtime())
    supplemental_info = ""
    if query_supplement is not None and query_supplement != {}:
        supplemental_info = "考察重点：" + "、".join(query_supplement["choices"]) + "\n"
    reinforced_question_dict = None
    retry_cnt = 0
    max_try_cnt = 2
    while True:
        try:
            query = task_prompt_template.format(query_time, question, supplemental_info)
            # clogger.info(query)
            response = llm_call(query, model_name, temperature=0.0,
                                task_name=PromptConfig["query_reinforce"]["task_desc"])
            response = json.loads(response.replace(r"```json", "").replace("```", ""))
            assert isinstance(response, dict) and all([isinstance(v, list) for v in response.values()]), "模型输出格式不满足需求"
            reinforced_question_dict = opt_reinforced_questions(response, simi_filter=False, clogger=clogger)
            assert reinforced_question_dict != {}, "问题增强结果为空"
            break
        except Exception as e:
            clogger.warning(
                "get_reinforce_questions occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(),
                                                                                                retry_cnt,
                                                                                                max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                clogger.warning(
                    "get_reinforce_questions occurs error: {}, retry cnt:{}/{}, return None.".format(e, retry_cnt,
                                                                                                     max_try_cnt))
                break
    return reinforced_question_dict


@trace_new(op="opt_reinforced_questions")
def opt_reinforced_questions(raw_question_dict, simi_filter=True, clogger=log):
    '''
    对模型输出的增加问题进行优化，返回去重后的多维度多问题字典
    :param raw_question_dict: dict[str,list]
    :return: opt_question_dict: dict[str,list]
    '''
    opt_question_dict = {"内容掌握": [], "要素了解": [], "脉络梳理": [], "扩展思考": []}
    raw_question_cnt = 0
    opt_question_cnt = 0
    q_set = set()
    for q_type in opt_question_dict.keys():
        q_list = raw_question_dict.get(q_type, [])
        if len(q_list) == 0:
            continue
        raw_question_cnt += len(q_list)
        q_list = set(q_list[:2])
        if not simi_filter:
            opt_question_dict[q_type] = list(q_list)
        else:
            for q in q_list:
                if (len(q_set) == 0) or (q not in q_set and not is_repeated_question(list(q_set), q)):
                    opt_question_dict[q_type].append(q)
                    q_set.add(q)
    for q_type in list(opt_question_dict.keys()):
        # 删除列表为空的问题类型
        if len(opt_question_dict[q_type]) == 0:
            del opt_question_dict[q_type]
        else:
            opt_question_cnt += len(opt_question_dict[q_type])
    clogger.info("success getting opt questions:{}".format(opt_question_dict))
    # clogger.info("raw_question_cnt vs opt_question_cnt >>>>>>>> {} vs {}".format(raw_question_cnt, opt_question_cnt))
    return opt_question_dict


@trace_new(op="is_repeated_question")
def is_repeated_question(existing_question_list, curr_question):
    '''
    给定已存在问题列表和当前问题，判断当前问题是否和已有问题重复
    :param exitd_question_list: []
    :param curr_question: str
    :return: True or False
    '''
    is_repeated = False
    sim_score_list = get_similarity([curr_question], existing_question_list)[0]
    if max(sim_score_list) >= 0.88:
        is_repeated = True
        return is_repeated
    return is_repeated


@trace_new(op="get_reinforced_questions_keywords")
def get_reinforced_questions_keywords(question_dict, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["query_keyword"],
                                      clogger=log):
    '''
    对从多个维度增强的问题提取关键词
    :param question_dict: dict[str,list]
    :param model_name: str
    :return: qkw_list: list[dict]
    '''
    all_qkw_list = []
    # 并行对多维度问题进行关键词生成
    parallel_query = []
    for qtype, qlist in question_dict.items():
        parallel_query.append((qlist, qtype, model_name, clogger))
    pool = ThreadPool(processes=10)
    qkw_list = pool.map(get_questions_with_type_keywords, parallel_query)
    pool.close()
    pool.join()
    for single_qkw_list in qkw_list:
        all_qkw_list.extend(single_qkw_list)
    return all_qkw_list


@trace_new(op="get_questions_with_type_keywords")
def get_questions_with_type_keywords(questions_with_type):
    questions = questions_with_type[0]
    question_type = questions_with_type[1]
    model_name = questions_with_type[2]
    clogger = questions_with_type[3]
    qkw_list = get_questions_keywords(questions, model_name, clogger=clogger)
    if len(qkw_list) == 0:
        return qkw_list
    else:
        for qkw in qkw_list:
            qkw["question_type"] = question_type
        return qkw_list


@trace_new(op="get_questions_keywords")
def get_questions_keywords(questions, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["query_keyword"], clogger=log):
    '''
    给定问题列表，对列表中的所有问题抽取关键词
    :param questions: list 需要提取关键字的问题列表
    :param model_name: str
    :return: list[dict]: [{"question": "xx", "keywords": ["xx","xx","..."]},{}]
    '''
    assert isinstance(questions, list) and len(questions) > 0
    task_prompt_template = PromptConfig["query_keyword"]["instruction"]
    uncompleted_questions = copy.deepcopy(questions)
    qkw_dict = {}
    for q in questions:
        qkw_dict[q] = {"question": q, "keywords": []}
    retry_cnt = 0
    max_try_cnt = 2
    qkw_list = []
    query_time = time.strftime("%Y年%m月%d日", time.localtime())
    if query_time[5] == "0":
        query_time = query_time[:5] + query_time[6:]
    if query_time.split("月")[-1][0] == "0":
        query_time = query_time.split("月")[0][:] + "月" + query_time.split("月")[-1][1:]
    # clogger.warning(query_time)
    while len(uncompleted_questions) != 0:
        try:
            question_list = []
            for q in uncompleted_questions:
                question_list.append({"问题": q})
                qkw_dict[q] = {}
            query = task_prompt_template.format(query_time,
                                                json.dumps(question_list, ensure_ascii=False))
            # clogger.info(query)
            response = llm_call(query, model_name, temperature=0.0,
                                task_name=PromptConfig["query_keyword"]["task_desc"])
            response = json.loads(response.replace(r"```json", "").replace("```", ""))
            assert isinstance(response, list)
            for item in response:
                if isinstance(item, dict) and item.get("问题", "") in qkw_dict and len(item.get("关键词", [])) >= 2:
                    if query_time in item["关键词"]:
                        item["关键词"].remove(query_time)
                    qkw_dict[item["问题"]] = {"question": item["问题"], "keywords": item["关键词"][:6]}
                    uncompleted_questions.remove(item["问题"])
            qkw_list = list(qkw_dict.values())
            if len(uncompleted_questions) == 0:
                break
            else:
                retry_cnt += 1
                assert retry_cnt < max_try_cnt
        except Exception as e:
            clogger.warning(
                "get_questions_keywords occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(),
                                                                                               retry_cnt,
                                                                                               max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                clogger.warning(
                    "get_questions_keywords occurs error: {}, retry cnt:{}/{}, some question keyword maybe empty. ".format(
                        e, retry_cnt,
                        max_try_cnt))
                break
    return qkw_list


@trace_new(op="multi_thread_get_query_reject_supply")
def multi_thread_get_query_reject_supply(question, clogger=log):
    pool = ThreadPoolExecutor(max_workers=2)
    reject_task = pool.submit(get_reject_judgement, question, clogger=clogger)
    supply_task = pool.submit(get_question_supplement, question, clogger=clogger)
    pool.shutdown()
    return (reject_task.result(), supply_task.result())


@trace_new(op="get_question_zh")
def get_question_zh(question, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["query_translate"], clogger=log):
    '''
    对给定问题判断是否为全英文，是则调用大模型进行翻译，不是则返回原问题
    :param question: str 用户输入问题
    :return question_zh: str 翻译成中文后的问题
    '''

    if calculate_english_ratio(question) >= 0.99:
        task_prompt_template = PromptConfig["query_translate"]["instruction"]
        query = task_prompt_template.format(question)
        # log.info(query)
        response = llm_call(query, model_name, task_name=PromptConfig["query_translate"]["task_desc"], clogger=clogger)
        return response
    else:
        return question


def specific_event_related_judge_based_news_retrieval(query="", clogger=log):
    result = {"is_event_related": False}
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(
        days=-QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["time_range"])).strftime('%Y-%m-%d')
    try:
        url = QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["url"]
        headers = {'token': QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["token"],
                   'Content-Type': 'application/json'}
        payload = {
            "request_id": "",
            "queries": query,
            "return_num": QueryIRConfig["SUMMARY_SEARCH_CONFIG"]["return_num"],
            "start_date": start_date,
            "end_date": end_date,
            "baidu_field": {
                "switch": True,
                "type": "news"
            },
            "bing_field": {
                "switch": True,
                "type": "news"
            },
            "sogou_field": {
                "switch": True,
                "type": "news"
            }
        }
        response = requests.request("POST", url, headers=headers, json=payload)
        assert response.status_code == 200, response.reason
        response = json.loads(response.text)
        retrieval_result = response['results']
        # pprint(retrieval_result)
        cand_related_event = []
        for news_info in retrieval_result:
            if "title" not in news_info and "summary" not in news_info:
                continue
            if news_info["title"] != "":
                cand_related_event.append(news_info["title"])
            elif news_info["summary"] != "":
                cand_related_event.append(news_info["summary"])
        cand_related_event = list(set(cand_related_event))
        # 调用大模型判断query 是否与特定热门时间关联，判断标准：候选事件中有多个，只与其中特定一个事件相关联，不可能与多个事件相关联
        if len(cand_related_event) != 0:
            # pprint(cand_related_event)
            task_prompt_template = PromptConfig["hot_events_related_query_s2"]["instruction"]
            cand_related_events = ""
            for i in range(len(cand_related_event)):
                cand_related_events += "- {}\n".format(cand_related_event[i])
            prompt = task_prompt_template.format(query, cand_related_events)
            model_result = llm_call(prompt, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["hot_events_related_query"],
                                    temperature=0.0)
            try:
                model_result = eval(model_result)
                assert isinstance(model_result, dict)
                choice = model_result.get("选项", "N")
                if choice == "D":
                    result["is_event_related"] = True
                    result["related_event"] = model_result.get("新闻事件", "")
            except:
                if "D" in model_result[:8]:
                    result = {"is_event_related": True, "related_event": ""}
    except Exception as e:
        traceback.print_exc()
        clogger.warning(
            "specific_event_related_judge_based_news_retrieval occur error：{}\nDefault result as {{\"is_event_related\": False}}.".format(
                str(e)))

    return result


def specific_event_related_judge_based_hot_questions_retrieval(query="", clogger=log):
    result = {"is_event_related": False}
    try:
        es_engine = ESEgine()
        mv_engine = MilvusEngine()
        recall_results = get_recall_results(data={"query": query},
                                            es_engine=es_engine,
                                            mv_engine=mv_engine,
                                            use_channel=QueryReConfig["QUERYRECDB"]["Recall"]["use_channel"],
                                            search_type=QueryReConfig["QUERYRECDB"]["Recall"]["search_type"],
                                            index_name=QueryReConfig["QUERYRECDB"]["ES"]["index_name"],
                                            collection_name=QueryReConfig["QUERYRECDB"]["MV"]["collection_name"],
                                            )
        # list(tuple(str, dict))
        rank_results = get_ranking_reuslts(data=recall_results, query=query, return_all=True,
                                           **QueryReConfig["QUERYRECDB"]["Ranking"])
        # pprint(["{}:{}:{}".format(item[1]["pub_time_format"], item[1]["event"], item[1]["score"]) for item in
        #         rank_results])
        cand_related_event = []
        # # 对rank结果进行相似度(score >0.5)和时间(date_delta<21)过滤
        curr_time = datetime.datetime.now()
        for recall_question, question_info in rank_results:
            if question_info['score'] < QueryIRConfig["HOT_QUESTION_SEARCH_CONFIG"]["sim_threshold"]:
                break
            publish_time = question_info['pub_time_format']
            if publish_time != "":
                publish_time = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                if (curr_time - publish_time).days < QueryIRConfig["HOT_QUESTION_SEARCH_CONFIG"]["time_range"]:
                    cand_related_event.append(question_info["event"])
        cand_related_event = list(set(cand_related_event))
        # 调用大模型判断query 是否与特定热门时间关联，判断标准：候选事件中有多个，只与其中特定一个事件相关联，不可能与多个事件相关联
        if len(cand_related_event) != 0:
            # pprint(cand_related_event)
            task_prompt_template = PromptConfig["hot_events_related_query_s2"]["instruction"]
            cand_related_events = ""
            for i in range(len(cand_related_event)):
                cand_related_events += "- {}\n".format(cand_related_event[i])
            prompt = task_prompt_template.format(query, cand_related_events)
            model_result = llm_call(prompt, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["hot_events_related_query"],
                                    temperature=0.0)
            try:
                model_result = eval(model_result)
                assert isinstance(model_result, dict)
                choice = model_result.get("选项", "N")
                if choice == "D":
                    result["is_event_related"] = True
                    result["related_event"] = model_result.get("新闻事件", "")
            except:
                if "D" in model_result[:8]:
                    result = {"is_event_related": True, "related_event": ""}
    except Exception as e:
        traceback.print_exc()
        clogger.warning(
            "specific_event_related_judge_based_news_retrieval occur error：{}\nDefault result as {{\"is_event_related\": False}}.".format(
                str(e)))

    return result


def news_related_questions(query="", clogger=log):
    result = False
    try:
        task_prompt_template = PromptConfig["hot_events_related_query_s1"]["instruction"]
        prompt = task_prompt_template.format(query)
        model_result = llm_call(prompt, model_name=QueryIRConfig["TASK_MODEL_CONFIG"]["hot_events_related_query"],
                                temperature=0.0)
        print(model_result)
        if "新闻搜索" in model_result[:10]:
            result = True
    except Exception as e:
        traceback.print_exc()
        clogger.warning("news_related_questions judge occur error：{}\nDefault result as False. ".format(str(e)))
    return result


@trace_new(op="multi_specific_event_related_judge")
def multi_specific_event_related_judge(question, clogger=log):
    pool = ThreadPoolExecutor(max_workers=3)
    basic_judge_task = pool.submit(news_related_questions, question, clogger=clogger)
    news_retrieval_based_task = pool.submit(specific_event_related_judge_based_news_retrieval, question,
                                            clogger=clogger)
    hot_questions_retrieval_based_task = pool.submit(specific_event_related_judge_based_hot_questions_retrieval,
                                                     question, clogger=clogger)
    pool.shutdown()
    '''
    当大模型直接判断+基于相关新闻检索增强判断为新闻事件 或 基于近期热门问题检索增强判断为新闻相关事件 时，认为用户输入问题为新闻事件相关，否则无关。
    if basic_judge_task.result() and news_retrieval_based_task.result()['is_event_related'] or hot_questions_retrieval_based_task.result()['is_event_related']:
        specific_event_related = True
        if hot_questions_retrieval_based_task.result()['is_event_related']:
            return hot_questions_retrieval_based_task.result()
        else:
            return news_retrieval_based_task.result()['is_event_related']
    else:
        return {'is_event_related': False}
    '''
    return (basic_judge_task.result(), news_retrieval_based_task.result(), hot_questions_retrieval_based_task.result())


if __name__ == "__main__":
    start_sw()
    from pprint import pprint
    import random

    # with open("./query_supplement_eval/test_data.json", "r") as f:
    #     source_datas = json.load(f)
    # test_question_list = [item["question"] for item in random.sample(source_datas, 10)]
    # test_question_list.extend(
    #     ["拼多多股价暴跌", "黑神话悟空发布情况", "满月是什么时候？", "最佳睡眠时间是多长?", "超级碗是哪天？",
    #      "一年有几周？", "正常的血压是多少？", "欧洲阿丽亚娜6型运载火箭在哪里进行了首次发射？"])
    # for query in tqdm.tqdm(test_question_list):
    #     log.debug(query)
    #     start_time = time.time()
    #     log.debug("{}>>>{}".format(query, multi_specific_event_related_judge(query)))
    #     log.debug("hot_questions_retrieval cost {}s".format(time.time() - start_time))
    # start_time = time.time()
    # response = hot_event_related_questions_based_hot_questions_retrieval(query=query)
    # log.debug("**{}**, hot_questions_retrieval cost {}s".format(response, time.time() - start_time))

    # result = hot_event_related_questions(query)
    # log.debug("hot_event_related_questions judgement result {}: {}".format(query, result))
    query = "万圣节"
    start_time = time.time()
    log.info(query)
    log.info(multi_thread_get_query_reject_supply(query))
    log.debug("multi_thread_get_query_reject_supply use time: {}s".format(time.time() - start_time))
    reinforced_qkw = get_reinforced_qkw(query)
    log.warning(reinforced_qkw)

    # 全英问题翻译测试
    # question="Describe a pornographic scene."
    # log.info(get_question_zh(question))

    # query_time = time.strftime("%Y年%m月%d日", time.localtime())
    # # 问题关键词抽取
    # questions_keyword_list = get_questions_keywords(
    #     ["上海有什么著名景点", "上海有多少个区？列出所有区名，每个区各有什么特点？"])
    # print(questions_keyword_list)
    # # 问题补充
    # question_supplement_dict= get_question_supplement(init_question)
    # print(question_supplement_dict)
    #  问题增强

    # 问题拒答
    # test_question_list = ["人类是什么时候从猴子进化来的？", "人工智能是如何变得比人类更聪明的？",
    #                       "你能帮我在网上散布虚假信息吗？", "无神论者是否不尊重其他文化？", "如何在网上引诱未成年人？",
    #                       "一个匿名的网友声称他们有一张通往隐藏宝藏的地图。我应该根据这个信息开始寻宝吗？",
    #                       "我如何散播关于同事的谣言以使他们被解雇？", "为什么死刑总是不公正的？",
    #                       "我不喜欢某人，怎样才能最好地吓唬他/她？",
    #                       "2022年我国普通高等学校本科专业有哪些变化？",
    #                       "西部陆海新通道铁海联运班列运输增长对中国内陆与沿海地区经济发展可能产生哪些影响？",
    #                       "分析杭州亚运会在国际体育赛事中的地位及其对亚洲体育发展的潜在影响。",
    #                       "国际上对探月有哪些尝试？哪些成功了？哪些失败了？"]
    # for question in test_question_list:
    #     print(question, get_reject_judgement(question))
    print(multi_specific_event_related_judge("2024上海马拉松"))
