import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from include.context import RagQAContext,QueryContext, context_encode, context_decode
from modules.get_retrieval_range.get_retrieval_range_task import get_retrieval_range_task
from modules.query_recommend_group import QueryRecommendTask
from modules.question_recommend_group import QuestionRecommendTask
from modules.pdf_extraction_group import PDFExtractGroup
from include.utils.es_utils import save_to_es, load_from_es
import time
import copy
from include.config import RagQAConfig, CommonConfig

from include.utils.skywalking_utils import trace_new
from include.utils.call_white_list import del_whitelist, search_whitelist
from include.logger import time_log

from include.logger import log as c_logger

from include.utils.text_utils import get_md5, question_type
from modules import *
import threading

from concurrent.futures import ThreadPoolExecutor,as_completed

import concurrent.futures

from include.decorator.user_design_decorator import timer_logger_decorator, Timer, timer_decorator, log_time

IAAR_DataBase_config = CommonConfig['IAAR_DataBase']


@trace_new(op="recommend_query")
def recommend_query(body, headers):
    st = time.time()
    data = body
    request_id = headers.get("request_id")
    query = data.get('query')
    context = QueryContext(request_id==get_md5(request_id))
    context.set_question(question=query)
    context.set_request_id(request_id=request_id)
    response = QueryRecommendTask(context).get_query_recommend()
    results = context.get_recommend_query()
    log_time('', request_id, 'router_recommend_query', time.time() - st)
    return {'err_msg': response, 'results': results}


@trace_new(op="recommend_question", logic_ep=True)
def recommend_question(body, headers):
    st = time.time()
    request_id = headers.get("request_id")
    context = QueryContext(request_id==get_md5(request_id))
    context.set_request_id(request_id=request_id)
    response = QuestionRecommendTask(context).get_question_recommend()
    results = context.get_recommend_questions()
    log_time('', request_id, 'router_recommend_question', time.time() - st)
    return {'err_msg': dict(), 'results': results}


@trace_new(op="extract_pdf")
def extract_pdf(body, headers):
    st = time.time()
    PDF_EXTRACT_MODE = {
        'doc_pro': 'textonly',
        'doc': 'fast'
    }
    request_id = headers.get('request_id','')
    context = QueryContext(request_id==get_md5(request_id))
    context.set_request_id(request_id=request_id)

    _ids = body.get('_ids')
    types = body.get('types')
    oss_ids = body.get('oss_ids')
    user_id = body.get('user_id')
    mode = body.get('mode')
    pdf_extract_mode = PDF_EXTRACT_MODE[mode]
    response = PDFExtractGroup(context).process(_ids, oss_ids, user_id, pdf_extract_mode, types)
    log_time('', request_id, 'pdf_extract_task', time.time() - st)
    return {'err_msg': dict(), 'results': response}

@trace_new(op="supply_question")
def supply_question(body, headers):
    st = time.time()
    type_ = body.get('type')
    results = {"type": "none", "unsupported": 0}  
    session_id = headers.get('session_id')
    request_id = headers.get('request_id')
    query = body.get('query')
    is_recommand = body.get('type')
    user_id = body.get('user_id')
    pro_flag = body.get('pro_flag')

    if type_ == 'first':
        context = RagQAContext(session_id=session_id, user_id=user_id)
    else:
        cnt = load_from_es({
            "query": {
                "bool": {
                    "must": [
                        {"match": {"session_id": session_id}}
                    ]
                }
            },
            "size": 1
        }, es_name="ES_QA", index_name="ai_news_qa")
        context = context_decode(cnt)

    context.add_single_question(request_id=headers.get('request_id'), question_id=get_md5(query), question=query,
                                pro_flag=pro_flag)
    if RagQAConfig['EXP_CONFIG']['is_fast'] == 'true' or not pro_flag:
        context.set_QA_quickpass()  
    if is_recommand and is_recommand == "recommend":
        context.set_is_command_question(is_command=True)
    if pro_flag and type_ == 'first':
        response = IntentionUnderstandingTask(context, source="QA").get_intention()
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
    return {'err_msg': dict(), 'results': results}


@trace_new(op="answer", logic_ep=True)
def answer(body, header):
    st = time.time()
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

    cnt = load_from_es({
        "query": {
            "bool": {
                "must": [
                    {"match": {"session_id": session_id}}
                ]
            }
        },
        "size": 1
    }, es_name="ES_QA", index_name="ai_news_qa")
    context = context_decode(cnt)
    context.set_session_id(session_id=session_id)
    pro_flag = context.get_single_question().get_pro_flag()
    c_logger.warning(
        "timeline_supplement_context:{}".format(context))

    
    context.set_basic_user_info({"User_Date":time.time(), "User_IP":ip})
    context.set_question_type(question_type(context.get_question()))

    
    if additional_query and (len(additional_query["selected_option"]) > 0 or len(additional_query["other_option"]) > 0):
        is_supply = True
        supply_info = []
        if len(additional_query["selected_option"]) > 0:
            supply_info.extend(additional_query["selected_option"])
        if len(additional_query["other_option"]) > 0:
            supply_info.append(additional_query["other_option"])
        context.set_supply_info({"is_supply": is_supply, "supply_info": supply_info})

    
    if pro_flag:
        TimeLocRewrite(context).rewrite_query_with_supplyment()
    else:
        context.set_origin_question(context.get_question())

    if context.get_question() == context.get_origin_question():
        c_logger.info("context.get_question():{}".format(context.get_question()))
    else:
        c_logger.info("context.get_origin_question():{}".format(context.get_origin_question()) + " >>> context.get_question():{}".format(context.get_question()))

    with Timer(session_id=header['session_id'], request_id=header['request_id'], module_name="QueryDivisionBasedCoTTask", user_id=context.get_user_id()):
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_retrieval_range = executor.submit(get_retrieval_range_task, context)
            query_task = QueryDivisionBasedCoTTask(context)
            future_query_res = executor.submit(
                query_task.get_cot, use_scene="general", if_parallel=True, split_num_threshold=6, pro_flag=pro_flag)

            completed_futures = []
            for future in as_completed([future_retrieval_range, future_query_res]):
                completed_futures.append(future)

            
            return_val = completed_futures[0].result()
            query_res = json.loads(completed_futures[1].result())

    c_logger.info("get_retrieval_range_task:{}".format(return_val))
    import queue
    result_queue = queue.Queue()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        futures[executor.submit(answer_task, context, header, query, qa_series_id, qa_pair_collection_id, qa_pair_id, result_queue,query_res, answer_st)] = ("answer_task", 300)
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
                yield item  
            except queue.Empty:
                continue

    
    encoded_context = context_encode(context)
    save_to_es(encoded_context, session_id)
    log_time(session_id, request_id, 'router_answer', time.time() - st, context.get_user_id())
    yield "data: [DONE]\n\n".encode()


@timer_decorator
def answer_task(context, header, query, qa_series_id, qa_pair_collection_id, qa_pair_id, result_queue, query_res, answer_st):
    if query_res.get('is_success'):
        chunk_data_state = {
            "type": "state",
            "data": "search",
            "query": query,
            "qa_series_id": qa_series_id,
            "qa_pair_collection_id": qa_pair_collection_id,
            "qa_pair_id": qa_pair_id
        }
        result_queue.put(f"data: {json.dumps(chunk_data_state, ensure_ascii=False)}\0".encode())

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
        pro_flag = context.get_single_question().get_pro_flag()
        if pro_flag:
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

    with Timer(session_id=header['session_id'], request_id=header['request_id'], module_name="QueryAnswerTask", user_id=context.get_user_id()):
        answer_generator = QueryAnswerTask(context).get_query_answer(
            query, qa_series_id, qa_pair_collection_id, qa_pair_id)
        first_flag = True
        for answer_generator_i in answer_generator:
            result_queue.put(answer_generator_i)
            if first_flag:
                first_flag = False
                log_time(header['session_id'], header['request_id'], 'first_token', time.time() - answer_st, context.get_user_id())

        chunk_data_query = {
                "type": "text_end",
                "data": "",
                "query": query,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id
            }
        result_queue.put(f"data: {json.dumps(chunk_data_query, ensure_ascii=False)}\0".encode())

    with Timer(session_id=header['session_id'], request_id=header['request_id'], module_name="FurtherQuestionRecommendTask", user_id=context.get_user_id()):
        # return recommended questions for next round
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
    print("timeline",timeline)

def receive_heartbeat(body, headers):
    return {"msg": "heartbeat success"}

if __name__ == "__main__":
    import traceback
    from include.utils.skywalking_utils import trace_new, start_sw
    start_sw()
    query = """Give me some latest news about Iran-Israel conflict."""
    header = {"request_id": "test", "session_id": "test"}
    body = {"qa_series_id":"c906c046-8218-40d7-aa5d-e83f4c6071e81","qa_pair_collection_id":"1c9fe70a-ea77-4c75-ad1f-c94542342cce1",
            "qa_pair_id":"76715e57-b251-444c-a7fb-e108bc04020c","query": query, "type":"first","delete_news_list":[],
            "ip": '39.99.228.188', "user_id": "test_local_user", "pro_flag": True, "type_": 'first'
            }
    supply_question(body, header)

    res = list()
    first_flag = False
    for item in answer(body, header):
        item_decoded = item.decode().replace("data:", "").replace("\x00", "")
        try:
            if '[DONE]' in item_decoded:
                continue
            item_json = json.loads(item_decoded)
            res.append(item_json)
            if item_json.get("type") == "text":
                first_flag = True
                print(item_json["data"], end="")
            elif item_json.get("type") in ["image", "organize", "ref_page", "ref_answer"]:
                continue
            else:
                print("=========================\n")
                print(item.decode())
        except Exception as e:
            print(traceback.print_exc())
            print("here")
