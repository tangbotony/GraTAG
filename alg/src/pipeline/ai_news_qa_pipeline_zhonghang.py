from concurrent.futures import ThreadPoolExecutor
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import *
from include.context import RagQAContext
from include.utils.text_utils import get_md5
from include.logger import ContextLogger
import json
from include.utils.skywalking_utils import trace_new, start_sw
from modules.get_retrieval_range.get_retrieval_range_task import get_retrieval_range_task
from concurrent.futures import ThreadPoolExecutor, as_completed

start_sw()
from include.logger import time_log
from include.utils.text_utils import question_type


if __name__ == "__main__":
    cnt = 0
    # for query in open("../data/qa/waic.txt", "r"):
    for i in range(1):
        query = "长江治理的方法和效果有哪些"
        # query = "网传有武汉出租车司机请愿取消萝卜快跑，称「留口饭吃」，你愿意打无人驾驶车吗？无人车会取代常规出租车吗？"
        # query = "今天天气怎么样"
        query = "今年习近平两会行程"
        query = query.strip()
        context = RagQAContext(session_id=get_md5(query))
        context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
        context.set_QA_quickpass()    # 启用速通版本
        context.set_supply_info({"is_supply":False, "supply_info":["上海"]})
        context.set_question_type(question_type(context.get_question()))

        TimeLocRewrite(context).rewrite_query_with_supplyment()
        IntentionUnderstandingTask(context).get_intention()

        with ThreadPoolExecutor(max_workers=2) as executor:
            # 使用executor.submit提交任务
            future_retrieval_range = executor.submit(get_retrieval_range_task, context)
            query_task = QueryDivisionBasedCoTTask(context)
            future_query_res = executor.submit(query_task.get_cot,
                                               use_scene="general",
                                               if_parallel=True,
                                               split_num_threshold=3)

            completed_futures = []
            for future in as_completed([future_retrieval_range, future_query_res]):
                completed_futures.append(future)

            # 获取并返回执行结果
            return_val = completed_futures[0].result()
            query_res_dict = json.loads(completed_futures[1].result())

        context.set_retrieval_field({
            'iaar_database_kwargs': {'return_num': 100}
        })
        context.reset_reference()
        RecallTask(context).get_graph_recall(application='QuestionAnswer', graph=context.get_dag())
        candidate_images = context.get_fig_result(application='QuestionAnswer')

        # 生成答案
        answer_generator = QueryAnswerTask(context).get_query_answer(
            context.get_question(), "qa_series_id", "qa_pair_collection_id", "qa_pair_id",streaming=True)
        answer_list = []
        for answer in answer_generator:
            item_decoded = answer.decode().replace("data:", "").replace("\x00", "")
            item_json = json.loads(item_decoded)
            if item_json.get("type") == "text" and 'GraTAG type' not in item_json["data"]:
                print(item_json["data"], end="")
            elif isinstance(item_json, dict) and item_json['type'] == 'image':
                print("IMAGE: id: {}, url: {}".format(item_json['data'][-1]['id'], item_json['data'][-1]['url']))
            answer_list.append(item_json)
        ContextLogger(context).info("context.get_answer:{}".format(context.get_answer()))
        print(context.get_answer())
        # threadPool = ThreadPoolExecutor(max_workers=50, thread_name_prefix="test_")
        # all_task = [threadPool.submit(callQA, context),threadPool.submit(TimelineTask(context).get_timeline)]

        cnt += 1
        # if cnt > 0:
        #     break




