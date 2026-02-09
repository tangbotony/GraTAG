# coding:utf-8
#  XXXX模块
import copy
import json
import time
import argparse
from include.logger import log
from include.config import DocQAConfig


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="金融研报问题答案生成")
    parser.add_argument("--parallel_batch", default=1, help="")
    parser.add_argument("--exp_name", default="文档检索评估数据集合成-2", help="")
    parser.add_argument("--seed", default=3, help="")
    parser.add_argument("--samples_file_name",
                        default='evaluation_pipeline/all_samples', help="")
    parser.add_argument('--question_field', default=[''], help="所有的问题类型")
    parser.add_argument('--root_file', default='',
                        help="所有的问题类型")
    args = parser.parse_args()
    top_n_queries = 30
    search_field = {
        'file_database_kwargs': copy.deepcopy(DocQAConfig['IAAR_DataBase_Doc']['file_database_default_param'])
    }

    # 大模型过滤版
    all_base_results_base = []
    all_base_results_rerank_0829_sft_all_old_database = []
    all_base_results_rerank_base_all_old_database = []

    with open("AINews_DocQA_answer_文档检索评估数据集合成-2.json", 'r', encoding='utf-8') as file:
        all_chunks = json.load(file)

    for i, test_query_i_dict in enumerate(all_chunks[12:]):
        for ref in test_query_i_dict['reference']:
            from rag_recall_agent import RagRecall
            IAAR_DataBase_config = DocQAConfig['IAAR_DataBase_Doc']

            test_query_i = ref['query']
            search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param']}
            chunks = ref['chunks']

            my_rag_recall_gpt = RagRecall(
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

            my_rag_recall_ours = RagRecall(
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
                    "simi_bar": 0.5,
                    "model_name": 'gpt-4o',
                    "top_n": 30
                },
                min_num_chunks=5
            )

            my_rag_recall_base_rerank = RagRecall(
                user_info={
                    'application': 'GraTAG',
                    'session_id': "test_rag_recall_session_id",
                    'question_id': "test_rag_recall_question_id",
                    'request_id': time.time()
                },
                query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
                credible='false', auto_router_source='false',
                query_reinforce=False, similarity_config={
                    "method": 'rerank_base',  # base/llm/rerank/rerank_base
                    "is_filter": True,
                    "simi_bar": 0.5,
                    "model_name": 'gpt-4o',
                    "top_n": 30
                },
                min_num_chunks=5
            )

            # # 大模型过滤版
            # try:
            #     init_time = time.time()
            #     my_rag_recall_gpt.call_chunk_rank(copy.deepcopy(chunks))
            #     data_base_i = my_rag_recall_gpt.get_data_base()
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
            # # rerank_0829版
            # try:
            #     init_time = time.time()
            #     my_rag_recall_ours.call_chunk_rank(copy.deepcopy(chunks))
            #     data_base_i = my_rag_recall_ours.get_data_base()
            #     res_dict = {
            #         "test_query_i": test_query_i,
            #         "sorted_sources": data_base_i['use_for_check_items'],
            #         "time": time.time() - init_time
            #     }
            #     res_dict.update(test_query_i_dict)
            #     all_base_results_rerank_0829_sft_all_old_database.append(res_dict)
            # except:
            #     print("fail")
            # rerank_base版
            try:
                init_time = time.time()
                my_rag_recall_base_rerank.call_chunk_rank(copy.deepcopy(chunks))
                data_base_i = my_rag_recall_base_rerank.get_data_base()
                res_dict = {
                    "test_query_i": test_query_i,
                    "sorted_sources": data_base_i['use_for_check_items'],
                    "time": time.time() - init_time
                }
                res_dict.update(test_query_i_dict)
                all_base_results_rerank_base_all_old_database.append(res_dict)
            except:
                print("fail")

            # with open("0826_all_base_results_rerank_base-2.json", 'w', encoding="utf-8") as f:
            #     json.dump(all_base_results_base, f, indent=4, ensure_ascii=False)
            # with open("0826_all_base_results_rerank_sft_0829_all_old_database-2.json", 'w', encoding="utf-8") as f:
            #     json.dump(all_base_results_rerank_0829_sft_all_old_database, f, indent=4, ensure_ascii=False)
            with open("0826_all_base_results_rerank_base_all_old_database-2.json", 'w', encoding="utf-8") as f:
                json.dump(all_base_results_rerank_base_all_old_database, f, indent=4, ensure_ascii=False)
