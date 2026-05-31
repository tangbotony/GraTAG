# coding:utf-8
#  XXXX模块
import copy
import json
import time
from include.logger import log

from include.config import CommonConfig
from include.rag.rag_recall_agent import RagRecall

IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
rerank_config = CommonConfig['RERANK']


def read_txt_to_list_of_dict(file_path):
    # 初始化一个空列表来存储结果
    data_list = []

    # 读取txt文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 解析每一行并将其转换为字典
    for line in lines:
        # 移除行尾的换行符并按制表符（\t）分割
        columns = line.strip().split('\t')

        # 创建字典并添加到列表中
        data_dict = {
            'category': columns[0],
            'guidance_type': columns[1],
            'question': columns[2]
        }
        data_list.append(data_dict)

    return data_list


if __name__ == '__main__':
    data_list = read_txt_to_list_of_dict('evaluation_rag/evaluation_dataset.txt')

    # similarity 过滤版
    all_base_results_base = []
    # 大模型过滤版
    all_base_results_base_llm_filter_gpt_4o = []
    # new rerank版
    all_base_results_rerank_sft = []
    # new rerank_0828 版
    all_base_results_rerank_0828_sft = []
    # new rerank_0828 版
    all_base_results_rerank_0829_sft = []
    # new rerank_0828 版
    all_base_results_rerank_0829_sft_all_old_database = []
    # rerank_base版
    all_base_results_rerank_base = []

    all_chunks = []
    with open("rag_evaluation/0826_all_references.json", 'r', encoding='utf-8') as file:
        all_chunks = json.load(file)

    for i, test_query_i_dict in enumerate(data_list[:20]):
        category_i = test_query_i_dict['category']
        guidance_type_i = test_query_i_dict['guidance_type']
        test_query_i = test_query_i_dict['question']
        IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
        search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param']}

        # my_rag_recall = RagRecall(
        #     user_info={
        #         'application': 'GraTAG',
        #         'session_id': "test_rag_recall_session_id",
        #         'question_id': "test_rag_recall_question_id",
        #         'request_id': time.time()
        #     },
        #     query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
        #     credible='false', auto_router_source='false',
        #     query_reinforce=False, similarity_config={
        #         "method": 'base',  # base/llm/rerank
        #         "is_filter": True,
        #         "simi_bar": 0.6,
        #         "model_name": 'gpt-4o',
        #         "top_n": 30
        #     }
        # )
    #     sources = my_rag_recall.call_source()
    #     chunks = my_rag_recall.call_chunk_split(sources)
    #     all_chunks.append({
    #         "query": test_query_i,
    #         "chunks": chunks
    #     })
    #     with open("0826_all_references.json", 'w', encoding="utf-8") as f:
    #         json.dump(all_chunks, f, indent=4, ensure_ascii=False)

        chunks = all_chunks[i]['chunks']

        my_rag_recall1 = RagRecall(
            user_info={
                'application': 'GraTAG',
                'session_id': "test_rag_recall_session_id",
                'question_id': "test_rag_recall_question_id",
                'request_id': time.time()
            },
            query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
            credible='false', auto_router_source='false',
            query_reinforce=False, similarity_config={
                "method": 'base',  # base/llm/rerank
                "is_filter": True,
                "simi_bar": 0.6,
                "model_name": 'gpt-4o',
                "top_n": 30
            },
            min_num_chunks=0
        )
        my_rag_recall2 = RagRecall(
            user_info={
                'application': 'GraTAG',
                'session_id': "test_rag_recall_session_id",
                'question_id': "test_rag_recall_question_id",
                'request_id': time.time()
            },
            query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
            credible='false', auto_router_source='false',
            query_reinforce=False, similarity_config={
                "method": 'llm',  # base/llm/rerank
                "is_filter": True,
                "simi_bar": 0.6,
                "model_name": 'gpt-4o',
                "top_n": 30
            },
            min_num_chunks=0
        )
        my_rag_recall3 = RagRecall(
            user_info={
                'application': 'GraTAG',
                'session_id': "test_rag_recall_session_id",
                'question_id': "test_rag_recall_question_id",
                'request_id': time.time()
            },
            query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
            credible='false', auto_router_source='false',
            query_reinforce=False, similarity_config={
                "method": 'rerank-sft',  # base/llm/rerank
                "is_filter": True,
                "simi_bar": 0.5,
                "model_name": 'gpt-4o',
                "top_n": 30
            },
            min_num_chunks=0
        )

        my_rag_recall4 = RagRecall(
            user_info={
                'application': 'GraTAG',
                'session_id': "test_rag_recall_session_id",
                'question_id': "test_rag_recall_question_id",
                'request_id': time.time()
            },
            query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
            credible='false', auto_router_source='false',
            query_reinforce=False, similarity_config={
                "method": 'rerank_base',  # base/llm/rerank
                "is_filter": False,
                "simi_bar": 0.6,
                "model_name": 'gpt-4o',
                "top_n": 30
            },
            min_num_chunks=0
        )

        my_rag_recall5 = RagRecall(
            user_info={
                'application': 'GraTAG',
                'session_id': "test_rag_recall_session_id",
                'question_id': "test_rag_recall_question_id",
                'request_id': time.time()
            },
            query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
            credible='false', auto_router_source='false',
            query_reinforce=False, similarity_config={
                "method": 'rerank-sft-0829',  # base/llm/rerank/rerank_base
                "is_filter": True,
                "simi_bar": 0.8,
                "model_name": 'gpt-4o',
                "top_n": 30
            },
            min_num_chunks=5
        )

        # # 大模型过滤版
        # try:
        #     init_time = time.time()
        #     my_rag_recall1.call_chunk_rank(copy.deepcopy(chunks))
        #     data_base_i = my_rag_recall1.get_data_base()
        #     res_dict = {
        #         "test_query_i": test_query_i,
        #         "sorted_sources": data_base_i['use_for_check_items'],
        #         "time": time.time() - init_time
        #     }
        #     res_dict.update(test_query_i_dict)
        #     all_base_results_base.append(res_dict)
        # except:
        #     print("fail")
        #
        # # 大模型过滤版
        # try:
        #     init_time = time.time()
        #     my_rag_recall2.call_chunk_rank(copy.deepcopy(chunks))
        #     data_base_i = my_rag_recall2.get_data_base()
        #     res_dict = {
        #         "test_query_i": test_query_i,
        #         "sorted_sources": data_base_i['use_for_check_items'],
        #         "time": time.time() - init_time
        #     }
        #     res_dict.update(test_query_i_dict)
        #     all_base_results_base_llm_filter_gpt_4o.append(res_dict)
        # except:
        #     print("fail")
        #
        # # rerank版
        # try:
        #     init_time = time.time()
        #     my_rag_recall3.call_chunk_rank(copy.deepcopy(chunks))
        #     data_base_i = my_rag_recall3.get_data_base()
        #     res_dict = {
        #         "test_query_i": test_query_i,
        #         "sorted_sources": data_base_i['use_for_check_items'],
        #         "time": time.time() - init_time
        #     }
        #     res_dict.update(test_query_i_dict)
        #     all_base_results_rerank_sft.append(res_dict)
        # except:
        #     print("fail")
        #
        # # rerank_base版
        # try:
        #     init_time = time.time()
        #     my_rag_recall4.call_chunk_rank(copy.deepcopy(chunks))
        #     data_base_i = my_rag_recall4.get_data_base()
        #     res_dict = {
        #         "test_query_i": test_query_i,
        #         "sorted_sources": data_base_i['use_for_check_items'],
        #         "time": time.time() - init_time
        #     }
        #     res_dict.update(test_query_i_dict)
        #     all_base_results_rerank_base.append(res_dict)
        # except:
        #     print("fail")

        # rerank_0828版
        try:
            init_time = time.time()
            my_rag_recall5.call_chunk_rank(copy.deepcopy(chunks))
            data_base_i = my_rag_recall5.get_data_base()
            res_dict = {
                "test_query_i": test_query_i,
                "sorted_sources": data_base_i['use_for_check_items'],
                "time": time.time() - init_time
            }
            res_dict.update(test_query_i_dict)
            all_base_results_rerank_0829_sft_all_old_database.append(res_dict)
        except:
            print("fail")

        # with open("0826_all_base_results_base.json", 'w', encoding="utf-8") as f:
        #     json.dump(all_base_results_base, f, indent=4, ensure_ascii=False)
        # with open("0826_all_base_results_base_llm_filter_gpt_4o.json", 'w', encoding="utf-8") as f:
        #     json.dump(all_base_results_base_llm_filter_gpt_4o, f, indent=4, ensure_ascii=False)
        # with open("0826_all_base_results_rerank_sft.json", 'w', encoding="utf-8") as f:
        #     json.dump(all_base_results_rerank_sft, f, indent=4, ensure_ascii=False)
        # with open("0826_all_base_results_rerank_base.json", 'w', encoding="utf-8") as f:
        #     json.dump(all_base_results_rerank_base, f, indent=4, ensure_ascii=False)
        with open("rag_evaluation/0826_all_base_results_rerank_sft_0829_all_old_database.json", 'w', encoding="utf-8") as f:
            json.dump(all_base_results_rerank_0829_sft_all_old_database, f, indent=4, ensure_ascii=False)
