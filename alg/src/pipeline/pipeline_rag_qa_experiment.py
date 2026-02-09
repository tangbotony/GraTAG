import json
import time
import copy
import random
import hashlib
import argparse
import traceback
import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from include.logger import log
from concurrent.futures import ProcessPoolExecutor
from include.config import CommonConfig, RagQAConfig
from modules import *
from include.context import RagQAContext
from include.utils.text_utils import get_md5
from include.logger import ContextLogger
from modules.get_retrieval_range.get_retrieval_range_task import get_retrieval_range_task
from concurrent.futures import ThreadPoolExecutor, as_completed

es_user_config = CommonConfig['ES_USER']
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
from tqdm import tqdm

time_list = []


def get_chinese_date():
    # 获取今天的日期
    now = datetime.datetime.now()

    # 将日期时间格式化为中文格式：年-月-日 时:分:秒
    chinese_format_time = now.strftime('%Y年%m月%d日 %H时%M分%S秒')

    return chinese_format_time


date_time = get_chinese_date()


def store_answer(answer, content, exp_path):
    try:
        if answer:
            content_name = content.get('question')
            # 先查询对应的续写内容是不是已经存在，存在的话就不续写了；
            sha256 = hashlib.sha256()
            sha256.update(content_name.encode('utf-8'))
            selected_content_id = sha256.hexdigest() + 'multi_hop_general_xinhua0_0513'+str(time.time())

            # 插入一条结果
            data = {
                "_id": selected_content_id,
                "llm_sft_data": answer,
                "content": content
            }
            try:
                with open(exp_path, 'r') as file:
                    all_resl = json.load(file)
            except:
                all_resl = []
            with open(exp_path, 'w') as file:
                all_resl.append(data)
                json.dump(all_resl, file, indent=4, ensure_ascii=False)
            log.warning("Successfully stored the data!!!!!: {}".format(content_name))
    except Exception as e:
        log.error(e)
        log.error(traceback.print_exc())


def query_sft_get_explanation(content: dict, exp_path):
    this_query_time_dict = dict()
    this_query_time_dict['query'] = content['question']
    init_time = time.time()
    query = content['question']
    context = RagQAContext(session_id=get_md5(query), user_id="mock_user_id")
    context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
    if RagQAConfig['EXP_CONFIG']['is_fast'] == 'true':
        context.set_QA_quickpass()    # 启用速通版本，如果不启用则注释掉本行
    IntentionUnderstandingTask(context).get_intention()
    this_query_time_dict['IntentionUnderstandingTask'] = time.time() - init_time
    init_time = time.time()

    # 对问题进行重写
    TimeLocRewrite(context).rewrite_query_with_supplyment()
    if context.get_question() == context.get_origin_question():
        ContextLogger(context).info("context.get_question():{}".format(context.get_question()))
    else:
        ContextLogger(context).info("context.get_origin_question():{}".format(context.get_origin_question()) + " >>> context.get_question():{}".format(context.get_question()))

    # 使用executor.submit提交任务
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_retrieval_range = executor.submit(get_retrieval_range_task, context)
        query_task = QueryDivisionBasedCoTTask(context)
        future_query_res = executor.submit(query_task.get_cot,
                                           use_scene="general",
                                           if_parallel=True,
                                           split_num_threshold=6)

        completed_futures = []
        for future in as_completed([future_retrieval_range, future_query_res]):
            completed_futures.append(future)

    # 获取并返回执行结果
    return_val = completed_futures[0].result()
    query_res_dict = json.loads(completed_futures[1].result())

    this_query_time_dict['QueryDivisionBasedCoTTask'] = time.time() - init_time
    init_time = time.time()
    context.set_retrieval_field({
            'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])
    })
    context.reset_reference()
    RecallTask(context).get_graph_recall(application='QuestionAnswer', graph=context.get_dag())

    this_query_time_dict['RecallTask'] = time.time() - init_time
    init_time = time.time()

    # 生成答案
    final_answer_dict = QueryAnswerTask(context).get_query_answer_without_streaming(
        context.get_question(),
        "qa_series_id", "qa_pair_collection_id", "qa_pair_id")
    ContextLogger(context).info("context.get_answer:{}".format(context.get_answer()))
    this_query_time_dict['QueryAnswerTask'] = time.time() - init_time
    time_list.append(this_query_time_dict)

    print("time_list: ", time_list)
    if context.get_answer():
        store_answer(final_answer_dict, content, exp_path)
    return final_answer_dict, content


def res_write_output_func(contents, num_valid_text, parallel_batch, exp_path):
    need_checked_items = []
    for content in contents:
        content_name = content.get('question')
        # 先查询对应的续写内容是不是已经存在，存在的话就不续写了；
        sha256 = hashlib.sha256()
        sha256.update(content_name.encode('utf-8'))
        selected_content_id = sha256.hexdigest() + 'multi_hop_general_xinhua0_0513'
        content['id'] = selected_content_id
        need_checked_items.append(content)

    valid_text_this_iteraion = 0
    if need_checked_items:
        with ProcessPoolExecutor(max_workers=parallel_batch) as executor:
            # 提交所有任务并立即返回 Future 对象列表
            futures = [executor.submit(query_sft_get_explanation, item, exp_path) for item in need_checked_items]
            # 使用tqdm创建进度条
            res_all = []
            for future in tqdm(futures, total=len(futures), desc="Processing items"):
                res_all.append(future.result())  # 获取结果，同时更新进度条
        num_valid_text += len(res_all)
        valid_text_this_iteraion += len(res_all)
    return num_valid_text, valid_text_this_iteraion


if __name__ == '__main__':
    # Use a breakpoint in the code line below to debug your script.
    parser = argparse.ArgumentParser(description="通用问题答案生成")

    parser.add_argument("--parallel_batch", default=1, help="")
    parser.add_argument("--seed", default=3, help="")
    parser.add_argument("--exp_name", default='GraTAG_1103_non_pro', help="")

    # 解析命令行参数
    args = parser.parse_args()
    random.seed(args.seed)
    parallel_batch = args.parallel_batch
    data = []
    with open("../data/qa/iaar_150.txt", 'r', encoding='utf-8') as file:
        for line in file:
            data.append({"question": line.strip()})
    data = data[:]
    print("一共有{}组数据!!!".format(len(data)))
    num_valid_text = 0
    last_time = time.time()
    res_write_output_func(
        data, num_valid_text, parallel_batch,
        "../data/result/AINews_answer_{}.json".format(args.exp_name))
