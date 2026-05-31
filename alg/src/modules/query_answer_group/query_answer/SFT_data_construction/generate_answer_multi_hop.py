import json
import time
import random
import hashlib
import argparse
import pymongo
import traceback
from include.logger import log
from multiprocessing import Pool
from concurrent.futures import ProcessPoolExecutor
from include.utils.llm_caller_utils import llm_call
from include.query_answer.call_answer_func_multi_hop import call_answer_func_multi_hop

client = pymongo.MongoClient(host='localhost', port=27017)
db = client.open_domain_qa_multi_hop
my_mongo_db_data_answer = db.open_domain_qa_multi_hop_0513


def store_answer(answer, content):
    try:
        if answer:
            content_name = content.get('question')
            # 先查询对应的续写内容是不是已经存在，存在的话就不续写了；
            sha256 = hashlib.sha256()
            sha256.update(content_name.encode('utf-8'))
            selected_content_id = sha256.hexdigest() + 'multi_hop_general_0513'

            # 插入一条结果
            my_mongo_db_data_answer.insert_one({
                "_id": selected_content_id,
                "llm_sft_data": answer,
                "content": content
            })
            log.warning("Successfully stored the data!!!!!: {}".format(content_name))

            tmp = my_mongo_db_data_answer.count_documents({})

            print("=================================预测进度 {}%...........=====================".format(
                tmp / 5000 * 100))
    except Exception as e:
        log.error(e)
        log.error(traceback.print_exc())


def query_sft_get_explanation(content: dict):
    answer = None
    try:
        answer, modified_question = call_answer_func_multi_hop(content['question'], session_id=content['id'])
    except Exception as e:
        log.warning(e)
        log.warning(traceback.print_exc())
    if answer:
        answer["modified_question"] = modified_question
        store_answer(answer, content)
    return answer


#  单独句子的引证续写；改一下Pool 并发请求测试
# def basic_reference_write_by_sentence_v3(selected_content, **kwargs):
def res_write_output_func(contents, num_valid_text):
    need_checked_items = []
    for content in contents:
        content_name = content.get('question')
        # 先查询对应的续写内容是不是已经存在，存在的话就不续写了；
        sha256 = hashlib.sha256()
        sha256.update(content_name.encode('utf-8'))
        selected_content_id = sha256.hexdigest() + 'multi_hop_general_0513'
        content['id'] = selected_content_id
        find_res = my_mongo_db_data_answer.find_one({"_id": selected_content_id})
        if find_res is not None:
            print("已经产生过训练样例，略过....")
            continue
        need_checked_items.append(content)

    valid_text_this_iteraion = 0
    if need_checked_items:
        with ProcessPoolExecutor(max_workers=args.parallel_batch) as executor:
            # 提交所有任务并立即返回 Future 对象列表
            futures = [executor.submit(query_sft_get_explanation, item) for item in need_checked_items]
            # 获取结果
            res_all = [future.result() for future in futures]

        num_valid_text += len(res_all)
        valid_text_this_iteraion += len(res_all)
    return num_valid_text, valid_text_this_iteraion


if __name__ == '__main__':
    # Use a breakpoint in the code line below to debug your script.
    parser = argparse.ArgumentParser(description="通用问题答案生成")

    # 添加命令行参数
    parser.add_argument("--num-queries", default=1000, help="")
    parser.add_argument("--parallel_batch", default=3, help="")
    parser.add_argument("--seed", default=3, help="")

    # 解析命令行参数
    args = parser.parse_args()

    random.seed(args.seed)

    with open("../dataset/dureader2_0/preprocessed/trainset/train.jsonl", 'r', encoding='utf-8') as file:
        # 逐行读取
        data = [json.loads(line) for line in file]

    # 开始做一下并发执行和写入mongodb
    data = data[:args.num_queries * 2]
    random.shuffle(data)
    data = data[:args.num_queries]

    print("一共有{}组数据!!!".format(len(data)))

    num_valid_text = 0
    batch_num = 0
    last_time = time.time()

    res_write_output_func(data, num_valid_text)