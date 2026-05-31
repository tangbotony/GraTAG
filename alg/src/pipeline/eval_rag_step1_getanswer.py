import json
import sys, os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from include.context import RagQAContext, QueryContext, context_encode, context_decode
from modules.get_retrieval_range.get_retrieval_range_task import get_retrieval_range_task
from modules.query_recommend_group import QueryRecommendTask
from modules.question_recommend_group import QuestionRecommendTask
from include.utils.es_utils import save_to_es, load_from_es
import time
import copy
from include.config import RagQAConfig, CommonConfig
from include.utils.skywalking_utils import trace_new
from include.utils.call_white_list import del_whitelist, search_whitelist
from include.logger import log as c_logger
from include.utils.text_utils import get_md5, question_type
from modules import *
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from include.decorator.user_design_decorator import timer_logger_decorator, Timer, timer_decorator, log_time
from include.utils.webhook_utils import WEBHOOK_SECRET, LarkBot

time_lark_bot = LarkBot(WEBHOOK_SECRET)

IAAR_DataBase_config = CommonConfig['IAAR_DataBase']


@trace_new(op="recommend_query")
def recommend_query(body, headers):
    st = time.time()
    data = body
    request_id = headers.get("request_id")
    query = data.get('query')
    return_all = data.get('return_all', False)
    # 还需要参数校验
    context = QueryContext(request_id == get_md5(request_id))
    context.set_question(question=query)
    context.set_request_id(request_id=request_id)
    context.set_return(return_all=return_all)
    # 业务逻辑
    response = QueryRecommendTask(context).get_query_recommend()
    results = context.get_recommend_query()
    log_time('', request_id, 'router_recommend_query', time.time() - st)
    return {'err_msg': response, 'results': results}


@trace_new(op="recommend_question", logic_ep=True)
def recommend_question(body, headers):
    # 无传参
    st = time.time()
    request_id = headers.get("request_id")
    context = QueryContext(request_id == get_md5(request_id))
    context.set_request_id(request_id=request_id)
    response = QuestionRecommendTask(context).get_question_recommend()
    results = context.get_recommend_questions()
    log_time('', request_id, 'router_recommend_question', time.time() - st)
    # return 1
    return {'err_msg': dict(), 'results': results}


@trace_new(op="supply_question")
def supply_question(body, headers, time_record):
    st = time.time()
    results = {"type": "none", "unsupported": 0}  # 默认不拒答不补充不错误提示
    session_id = headers.get('session_id')
    request_id = headers.get('request_id')
    query = body.get('query')
    is_recommand = body.get('type')
    user_id = body.get('user_id')
    pro_flag = body.get('pro_flag')

    context = RagQAContext(session_id=session_id, user_id=user_id)
    context.add_single_question(request_id=headers.get('request_id'), question_id=get_md5(query), question=query,
                                pro_flag=pro_flag)
    if RagQAConfig['EXP_CONFIG']['is_fast'] == 'true' or not pro_flag:
        context.set_QA_quickpass()  # 启用速通版本，如果不启用则注释掉本行
    if is_recommand and is_recommand == "recommend":
        context.set_is_command_question(is_command=True)
    if pro_flag:
        response = IntentionUnderstandingTask(context).get_intention()
        response = json.loads(response)
        encoded_context = context_encode(context)
        save_to_es(encoded_context, session_id)
        if response["is_success"]:
            question_rejection = context.get_question_rejection()
            if question_rejection["is_reject"]:
                results["type"] = "reject"
            else:
                if question_rejection.get("reject_reason", "") == '图表生成类问题':
                    results["unsupported"] = 1
                question_supplement = context.get_question_supplement()
                if question_supplement["is_supply"]:
                    results["type"] = "additional_query"
                    results["additional_query"] = {"title": question_supplement["supply_description"],
                                                   "options": question_supplement["supply_choices"]}
        log_time(session_id, headers.get('request_id'), 'router_supply_question', time.time() - st)
    else:
        encoded_context = context_encode(context)
        save_to_es(encoded_context, session_id)
    if context.get_question() not in time_record:
        time_record[context.get_question()] = dict()
    time_record[context.get_question()]['supply_question'] = time.time() - time_record['init_time']
    return {'err_msg': dict(), 'results': results}, context


@trace_new(op="answer", logic_ep=True)
def answer(body, header, context, time_record):
    st = time.time()
    time_init = st
    answer_st = st
    query = body.get('query')
    ip = body.get('ip', '')
    qa_series_id = body.get('qa_series_id')
    qa_pair_collection_id = body.get('qa_pair_collection_id')
    qa_pair_id = body.get('qa_pair_id')
    delete_news_list = body.get('delete_news_list')
    type = body.get('type')
    additional_query = body.get('additional_query', None)

    request_id = header.get('request_id')
    session_id = header.get('session_id')
    # 还需要参数校验

    # cnt = load_from_es({
    #     "query": {
    #         "bool": {
    #             "must": [
    #                 {"match": {"session_id": session_id}}
    #             ]
    #         }
    #     },
    #     "size": 1
    # }, es_name="ES_QA", index_name="ai_news_qa")
    # context = context_decode(cnt)
    context.set_session_id(session_id=session_id)
    pro_flag = context.get_single_question().get_pro_flag()
    # c_logger = get_logger(context)
    c_logger.warning(
        "timeline_supplement_context:{}".format(context))

    # context.add_single_question(request_id=request_id, question_id=get_md5(query), question=query)
    context.set_basic_user_info({"User_Date": time.time(), "User_IP": ip})
    context.set_question_type(question_type(context.get_question()))

    # 用户选择或输入的信息补充写入context, 非pro版没有信息补充环节，所以不用改写
    if additional_query and (len(additional_query["selected_option"]) > 0 or len(additional_query["other_option"]) > 0):
        is_supply = True
        supply_info = []
        if len(additional_query["selected_option"]) > 0:
            supply_info.extend(additional_query["selected_option"])
        if len(additional_query["other_option"]) > 0:
            supply_info.append(additional_query["other_option"])
        context.set_supply_info({"is_supply": is_supply, "supply_info": supply_info})
        # if len(supply_info)>0:
        #     c_logger.info("context.get_question():{}".format(context.get_question()))
        # context.set_question(context.get_question()+" "+ ",".join(supply_info))
        # c_logger.info("context.get_question():{}".format(context.get_question()))

    # 对问题进行重写
    if pro_flag:
        TimeLocRewrite(context).rewrite_query_with_supplyment()
    else:
        context.set_origin_question(context.get_question())

    if context.get_question() == context.get_origin_question():
        c_logger.info("context.get_question():{}".format(context.get_question()))
    else:
        c_logger.info("context.get_origin_question():{}".format(context.get_origin_question()) + " >>> context.get_question():{}".format(context.get_question()))

    with Timer(session_id=header['session_id'], request_id=header['request_id'], module_name="QueryDivisionBasedCoTTask", user_id=context.get_user_id()):
        # 获取时间窗口和general cot
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 使用executor.submit提交任务
            future_retrieval_range = executor.submit(get_retrieval_range_task, context)
            query_task = QueryDivisionBasedCoTTask(context)
            future_query_res = executor.submit(
                query_task.get_cot, use_scene="general", if_parallel=True, split_num_threshold=6, pro_flag=pro_flag)

            completed_futures = []
            for future in as_completed([future_retrieval_range, future_query_res]):
                completed_futures.append(future)

            # 获取并返回执行结果
            return_val = completed_futures[0].result()
            query_res = json.loads(completed_futures[1].result())

    c_logger.info("get_retrieval_range_task:{}".format(return_val))

    if context.get_question() not in time_record:
        time_record[context.get_question()] = dict()
    time_record[context.get_question()]['TimeLocRewrite & cot'] = time.time() - time_record['init_time']

    import queue
    result_queue = queue.Queue()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        futures[executor.submit(answer_task, context, header, query, qa_series_id, qa_pair_collection_id, qa_pair_id,
                                result_queue, query_res, answer_st, time_init, time_record)] = ("answer_task", 300)
        if pro_flag:
            futures[executor.submit(timeline_task, context, query, qa_series_id, qa_pair_collection_id, qa_pair_id, result_queue)] = ("timeline_task", 300)
        st = time.time()
        while any(future.running() for future in futures) or not result_queue.empty():
            for future in list(futures.keys()):
                item = futures[future]
                if item[1] < time.time() - st:
                    chunk_data_query = {
                        "type": "error",
                        "data": f"timeout for {item[0]}",
                        "query": query,
                        "qa_series_id": qa_series_id,
                        "qa_pair_collection_id": qa_pair_collection_id,
                        "qa_pair_id": qa_pair_id
                    }
                    yield f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode()
                    futures.pop(future)

            try:
                item = result_queue.get(timeout=0.1)
                yield item  # 流式返回每个结果项
            except queue.Empty:
                continue

    # 结束时需要有如下的标识符
    encoded_context = context_encode(context)
    save_to_es(encoded_context, session_id)

    yield "data: [DONE]\n\n".encode()
    log_time(session_id, request_id, 'router_answer', time.time() - st, context.get_user_id())


@timer_decorator
def answer_task(context, header, query, qa_series_id, qa_pair_collection_id, qa_pair_id, result_queue, query_res, answer_st, time_init, time_record):
    if query_res.get('is_success'):
        # 返回状态，query 扩写结束，进入检索阶段
        chunk_data_state = {
            "type": "state",
            "data": "search",
            "query": query,
            "qa_series_id": qa_series_id,
            "qa_pair_collection_id": qa_pair_collection_id,
            "qa_pair_id": qa_pair_id
        }
        result_queue.put(f"data: {json.dumps(chunk_data_state, ensure_ascii=False)}\0".encode())

        # 返回 query 扩写后的 query
        queries = context.get_dag().get_attr('need_rag')
        chunk_data_query = {
            "type": "intention_query",
            "data": queries,
            "query": query,
            "qa_series_id": qa_series_id,
            "qa_pair_collection_id": qa_pair_collection_id,
            "qa_pair_id": qa_pair_id
        }
        result_queue.put(f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode())
    else:
        # 问题扩写失败，直接结束，返回错误答案
        chunk_data_query = {
            "type": "error",
            "data": query_res.get('detail'),
            "query": query,
            "qa_series_id": qa_series_id,
            "qa_pair_collection_id": qa_pair_collection_id,
            "qa_pair_id": qa_pair_id
        }
        result_queue.put(f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode())
        result_queue.put("data: [DONE]\n\n".encode())
    with Timer(session_id=header['session_id'], request_id=header['request_id'], module_name="RecallTask", user_id=context.get_user_id()):
        # 检索召回
        pro_flag = context.get_single_question().get_pro_flag()
        if pro_flag:  # pro版
            search_field = {'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])}
        else:
            search_field = {'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param_pro_flag'])}

        context.set_retrieval_field(search_field)

        ref_page = None
        if RagQAConfig["WHITE_LIST_CONFIG"]["is_use"] == 'true':
            try:
                whitelist_response = search_whitelist(
                    scheme_id=RagQAConfig["WHITE_LIST_CONFIG"]["query_answer"]["scheme_id"],
                    input_info={"query": context.get_question()})
                if whitelist_response is not None:
                    cache_result = whitelist_response[0]['output']
                    stream_info, ref_answer, ref_page = (cache_result['stream_info'],
                                                         cache_result['ref_answer'],
                                                         cache_result['ref_page'],)
            except Exception as e:
                print("error during search_white_list")

        if not ref_page:
            recall_res = RecallTask(context).get_graph_recall(application='QuestionAnswer', graph=context.get_dag())
            if recall_res.get('is_success'):
                # 返回 召回数据
                ref_page = context.get_references_result_doc()
            else:
                chunk_data_state = {
                    "type": "error",
                    "data": "recall error",
                    "query": query,
                    "qa_series_id": qa_series_id,
                    "qa_pair_collection_id": qa_pair_collection_id,
                    "qa_pair_id": qa_pair_id
                }
                result_queue.put(f"data: {json.dumps(chunk_data_state, ensure_ascii=False)}\0".encode())
        if ref_page:
            chunk_data_state = {
                "type": "state",
                "data": "organize",
                "query": query,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id
            }
            result_queue.put(f"data: {json.dumps(chunk_data_state, ensure_ascii=False)}\0".encode())
            chunk_data_query = {
                "type": "ref_page",
                "data": ref_page,
                "query": query,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id
            }
            result_queue.put(f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode())

    if context.get_question() not in time_record:
        time_record[context.get_question()] = dict()
    time_record[context.get_question()]['recall'] = time.time() - time_record['init_time']

    with Timer(session_id=header['session_id'], request_id=header['request_id'], module_name="QueryAnswerTask",
               user_id=context.get_user_id()):
        # 问答
        context.get_single_question()._time_record = time_record
        answer_generator = QueryAnswerTask(context).get_query_answer(
            query, qa_series_id, qa_pair_collection_id, qa_pair_id)
        first_flag = True
        for answer_generator_i in answer_generator:
            result_queue.put(answer_generator_i)
            if first_flag:
                first_flag = False
                send_data = '''- **session_id: {}**\n- **request_id: {}**\n- **cost_time: {}**\n- **user id: {}** \n'''.format(
                    header['session_id'], header['request_id'], time.time() - answer_st, context.get_user_id())
                time_lark_bot.send_card(context.get_user_id(), "First Token", send_data)
                log_time(header['session_id'], header['request_id'], 'first_token', time.time() - answer_st,
                         context.get_user_id())

        chunk_data_query = {
            "type": "text_end",
            "data": "",
            "query": query,
            "qa_series_id": qa_series_id,
            "qa_pair_collection_id": qa_pair_collection_id,
            "qa_pair_id": qa_pair_id
        }
        result_queue.put(f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode())

    with Timer(session_id=header['session_id'], request_id=header['request_id'],
               module_name="FurtherQuestionRecommendTask", user_id=context.get_user_id()):
        # 返回追问推荐
        response = FurtherQuestionRecommendTask(context).get_further_question_recommend()
        further_quetions = context.get_further_recommend_questions()
        chunk_further_quetions = {
            "type": "recommendation",
            "data": further_quetions,
            "query": query,
            "qa_series_id": qa_series_id,
            "qa_pair_collection_id": qa_pair_collection_id,
            "qa_pair_id": qa_pair_id
        }
        result_queue.put(f"data: {json.dumps(chunk_further_quetions, ensure_ascii=False)}\0".encode())


@timer_decorator
def timeline_task(context, query, qa_series_id, qa_pair_collection_id, qa_pair_id, result_queue):
    TimelineTask(context).get_timeline(context)

    # 事件脉络参考资料
    # timeline_reference = context.get_timeline_reference()
    # chunk_data_query = {
    #     "type": "ref_page",
    #     "data": timeline_reference,
    #     "query": query,
    #     "qa_series_id": qa_series_id,
    #     "qa_pair_collection_id": qa_pair_collection_id,
    #     "qa_pair_id": qa_pair_id
    # }
    # result_queue.put(f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode())
    # 事件脉络结果
    timeline = context.get_timeline_highlight_events()
    chunk_timeline = {
        "type": "timeline",
        "data": timeline,
        "query": query,
        "qa_series_id": qa_series_id,
        "qa_pair_collection_id": qa_pair_collection_id,
        "qa_pair_id": qa_pair_id
    }
    result_queue.put(f"data: {json.dumps(chunk_timeline, ensure_ascii=False)}\0".encode())
    print("timeline", timeline)


def receive_heartbeat(body, headers):
    return {"msg": "heartbeat success"}


if __name__ == "__main__":
    import traceback
    from include.utils.skywalking_utils import trace_new, start_sw
    import json
    import os
    import tqdm
    start_sw()

    pro_flag = True
    is_continue = False
    exp_name = "qa_exam_241111_random_choose50_memory"  # ['exam_cmmlu', 'exam_version_241104', 'qa_exam_241111_random_choose50'# ]
    file_path = os.path.join("../data", "qa", "iaar_150_json.json")
    save_path = os.path.join("../data", "qa", "iaar_50_json_res_no_rawrank_1.json")
    save_root, _ = os.path.split(save_path)
    if not os.path.exists(save_root):
        os.makedirs(save_root)
    save_list = []
    exist_question = []
    exist_data = []

    with open(file_path,'r',encoding='utf-8') as input_file:
        file_content_all=json.load(input_file)
    if is_continue:
        if os.path.exists(save_path):
            with open(save_path,'r',encoding='utf-8') as input_file:
                exist_data=json.load(input_file)
    # 获取已有数据
    for exist_data_i in exist_data:
        llm_response=exist_data_i.get("llm_response","")
        if llm_response:
            exist_question.append(exist_data_i['question'])
    # 判断哪些数据应该处理
    file_content = []
    for file_content_i in file_content_all:
        if file_content_i['question'] not in exist_question:
            file_content.append(file_content_i)

    def process_question_item(question_item, header, time_record):
        question = question_item["question"]
        query = f"{question}"

        body = {
            "qa_series_id": "c906c046-8218-40d7-aa5d-e83f4c6071e81",
            "qa_pair_collection_id": "1c9fe70a-ea77-4c75-ad1f-c94542342cce1",
            "qa_pair_id": "76715e57-b251-444c-a7fb-e108bc04020c",
            "query": query,
            "type": "first",
            "delete_news_list": [],
            "additional_query": {
                "options": ["北京", "上海", "广州", "深圳"],
                "other_option": "",
                "selected_option": [],
                "title": "请选择您想了解的具体地点："
            },
            "ip": '39.99.228.188',
            "user_id": "test123",
            "pro_flag": pro_flag
        }

        # Initialize a time record for each question
        time_record["init_time"] = time.time()
        _, context = supply_question(body, header, time_record)

        res = []
        first_token = False
        first_token_time = 0.0
        init_time = time.time()
        try:
            for item in answer(body, header, context, time_record):
                item_decoded = item.decode().replace("data:", "").replace("\x00", "")
                if '[DONE]' in item_decoded:
                    continue
                item_json = json.loads(item_decoded)
                res.append(item_json)

                if item_json.get("type") == "text":
                    if not first_token:
                        first_token_time = time.time() - init_time
                        if context.get_question() not in time_record:
                            time_record[context.get_question()] = dict()
                        time_record[context.get_question()]['first_token_outside'] = time.time() - time_record[
                            'init_time']
                    first_token = True
                    print(item_json["data"], end="")
                elif item_json.get("type") in ["image", "organize", "ref_page", "ref_answer"]:
                    continue
                else:
                    print("=========================\n")
                    print(item.decode())
        except Exception as e:
            traceback.print_exc()
            print("Error encountered:", e)

        # Capture final answer and other data for the question item
        question_item["llm_response"] = context.get_answer()
        question_item["llm_input"] = re.sub(r'[\ud800-\udfff]', '', context.get_llm_final_input())
        question_item['first_token'] = first_token_time
        question_item["time_record"] = time_record  # Append time record for tracking

        return question_item


    header = {"request_id": "gyhtest", "session_id": "gyhtest"}

    # Use ThreadPoolExecutor to parallelize processing of each question item
    with concurrent.futures.ThreadPoolExecutor(1) as executor:
        # Process each question item in parallel
        futures = {
            executor.submit(process_question_item, question_item, header, {}): question_item
            for question_item in file_content[:50]
        }

        for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            try:
                result = future.result()
                exist_data.append(result)
                with open(save_path, 'w', encoding='utf-8') as save_file:
                    json.dump(exist_data, save_file, indent=4, ensure_ascii=False)
            except Exception as e:
                print("An error occurred:", e)