from include.logger import time_log

from pipeline.functions import supply_question, answer

import uuid
import time
import concurrent.futures
import tqdm
import json
import traceback


def one_execute(query):

    session_id = str(uuid.uuid4()) + "_test1"
    request_id = str(uuid.uuid4()) + "_test1"
    body = {"query": query, "type": "fisrt"}
    header = {"session_id": session_id, "request_id": request_id}
    st = time.time()
    try:
        supply_question(body, header)
    except Exception as e:
        traceback.print_exc()
        # time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": "supply_question", "status": "error", "error": str(e)}, ensure_ascii=False))
        return
    ed = time.time()
    cost_time = ed - st
    # time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": "supply_question", "cost_time": cost_time}, ensure_ascii=False))


    body = {"query": query, "type": "fisrt", "ip": "xxx"}
    header = {"session_id": session_id, "request_id": request_id}
    st2 = time.time()
    try:
        result = answer(body, header)
        first_flag = False
        for item in result:
            content = item.decode('utf-8').strip("\0")
            # print("======================")
            # print(content)
            if content.startswith("data: ") and content != "data: [DONE]\n\n":
                content = content[len("data: "):]
                content = json.loads(content.strip())
                if content['type'] == 'error':
                    raise Exception(content['data'])
                if not first_flag and content['type'] == 'text':
                    first_flag = True
                    ed = time.time()
                    cost_time = ed - st
                    # time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": "first_token", "cost_time": cost_time}, ensure_ascii=False))

    except Exception as e:
        traceback.print_exc()
        # time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": "answer_and_timeline", "status": "error", "error": str(e)}, ensure_ascii=False))
        return
    ed = time.time()
    cost_time = ed - st2
    # time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": "answer_and_timeline", "cost_time": cost_time}, ensure_ascii=False))

    cost_time = ed - st
    # time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": "total", "cost_time": cost_time}, ensure_ascii=False))







def time_pipeline(input_file):

    input_queries = []
    with open(input_file) as file:
        for line in file:
            input_queries.append(line.strip())

    
    print(input_queries)
    input_queries = input_queries[:50]
    max_workers = 1
    # input_queries = ["简述北京奥运会"]

        # 使用 ThreadPoolExecutor 进行多线程调用
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 使用 tqdm 显示进度条
        with tqdm.tqdm(total=len(input_queries)) as pbar:
            futures = []
            for t in input_queries:
                future = executor.submit(one_execute, t)
                futures.append(future)
                
            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)  


