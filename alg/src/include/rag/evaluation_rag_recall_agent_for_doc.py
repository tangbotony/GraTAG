# coding:utf-8
#  XXXX模块
import copy
import json
import time
import argparse
import traceback
import concurrent.futures
from include.logger import log

from include.config import CommonConfig, DocQAConfig
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
rerank_config = CommonConfig['RERANK']
from modules.pdf_extraction_group.pdf_extraction.pdf_process import pdf_process


def store_answer(answer, answer_index, content, exp_path):
    try:
        if answer:
            content_name = content

            # 插入一条结果
            data = {
                "_id": answer_index,
                "reference": answer,
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="金融研报问题答案生成")
    parser.add_argument("--parallel_batch", default=1, help="")
    parser.add_argument("--exp_name", default="文档检索评估数据集合成", help="")
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
    all_base_results_base_llm_filter_gpt_4o = []
    all_base_results_rerank_0829_sft = []

    exp_path = "news_DocQA_answer_{}.json".format(args.exp_name)
    with open('{}.json'.format(args.samples_file_name), 'r', encoding='utf-8') as file:
        all_evaluation_data = json.load(file)
    evaluation_data = []
    for evaluation_data_i in all_evaluation_data:
        if any(substring in evaluation_data_i['doc_type'] for substring in args.question_field):
            evaluation_data.append(evaluation_data_i)

    def process_answer(data_i, index, max_try=5):
        qas_i = []
        if isinstance(data_i['doc_id'], str):
            oss_ids_input = ["{}{}".format("{}".format(args.root_file), data_i['doc_id'])]
        else:
            oss_ids_input = []
            for oss_id in data_i['doc_id']:
                oss_ids_input.append("{}{}".format("{}".format(args.root_file), oss_id))
        search_field['file_database_kwargs']['doc_id'] = oss_ids_input

        for oss_id in oss_ids_input:
            pdf_process('test1', oss_id, 'test123', mode='textonly', type_='pdf')

        try_i = 0
        while try_i <= max_try:
            try:
                from include.rag.rag_recall_agent import RagRecall
                if isinstance(data_i['question'], str):
                    my_rag_recall = RagRecall(
                        user_info={
                            'application': 'GraTAG',
                            'session_id': "test_rag_recall_session_id",
                            'question_id': "test_rag_recall_question_id",
                            'request_id': time.time(),
                            'user_id': 'test123'
                        },
                        query=data_i['question'], logger=log, search_field=copy.deepcopy(search_field),
                        credible='false', auto_router_source='false',
                        query_reinforce=False,
                        similarity_config={
                            "method": 'rerank-sft-0829',  # base/llm/rerank/rerank_base
                            "is_filter": True,
                            "simi_bar": 0.0,
                            "model_name": 'gpt-4o',
                            "top_n": 60
                        },
                        auto_retrieval_range=True,
                        min_num_chunks=3,
                        chunk_min_length=5,
                        max_chunk=60,
                    )
                    sources = my_rag_recall.call_source()
                    chunks = my_rag_recall.call_chunk_split(sources)
                    qas_i.append({
                        "query": data_i['question'],
                        "file": oss_ids_input,
                        "chunks": chunks
                    })
                else:
                    for query_i in data_i['question'][:top_n_queries]:
                        my_rag_recall = RagRecall(
                            user_info={
                                'application': 'GraTAG',
                                'session_id': "test_rag_recall_session_id",
                                'question_id': "test_rag_recall_question_id",
                                'request_id': time.time(),
                                'user_id': 'test123'
                            },
                            query=query_i, logger=log, search_field=copy.deepcopy(search_field),
                            credible='false', auto_router_source='false',
                            query_reinforce=False,
                            similarity_config={
                                "method": 'rerank-sft-0829',  # base/llm/rerank/rerank_base
                                "is_filter": True,
                                "simi_bar": 0.0,
                                "model_name": 'gpt-4o',
                                "top_n": 100
                            },
                            auto_retrieval_range=True,
                            chunk_min_length=5,
                            min_num_chunks=3,
                            max_chunk=60,
                        )
                        sources = my_rag_recall.call_source()
                        chunks = my_rag_recall.call_chunk_split(sources)
                        qas_i.append({
                            "query": query_i,
                            "file": oss_ids_input,
                            "chunks": chunks
                        })
                store_answer(qas_i, index, "".join(oss_ids_input), exp_path)
                return qas_i
            except:
                try_i += 1
        return None


    # 并行处理答案
    evaluation_data = evaluation_data[:]
    log.debug("共{}个任务".format(len(evaluation_data)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel_batch) as executor:
        future_to_answer = {
            executor.submit(process_answer, evaluation_data_i, evaluation_index, max_try=5):
                evaluation_data_i for evaluation_index, evaluation_data_i in enumerate(evaluation_data)}
        for future in concurrent.futures.as_completed(future_to_answer):
            res = future_to_answer[future]
            try:
                res_final = future.result()
            except Exception as exc:
                traceback.print_exc()
    #
    # all_chunks = []
    # with open("rag_evaluation/0826_all_references.json", 'r', encoding='utf-8') as file:
    #     all_chunks = json.load(file)
    #
    # for i, test_query_i_dict in enumerate(data_list[:20]):
    #     category_i = test_query_i_dict['category']
    #     guidance_type_i = test_query_i_dict['guidance_type']
    #     test_query_i = test_query_i_dict['question']
    #     IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
    #     search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param']}
    #
    #     chunks = all_chunks[i]['chunks']
    #
    #     my_rag_recall1 = RagRecall(
    #         user_info={
    #             'application': 'GraTAG',
    #             'session_id': "test_rag_recall_session_id",
    #             'question_id': "test_rag_recall_question_id",
    #             'request_id': time.time()
    #         },
    #         query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
    #         credible='false', auto_router_source='false',
    #         query_reinforce=False, similarity_config={
    #             "method": 'base',  # base/llm/rerank
    #             "is_filter": True,
    #             "simi_bar": 0.6,
    #             "model_name": 'gpt-4o',
    #             "top_n": 30
    #         },
    #         min_num_chunks=0
    #     )
    #     my_rag_recall2 = RagRecall(
    #         user_info={
    #             'application': 'GraTAG',
    #             'session_id': "test_rag_recall_session_id",
    #             'question_id': "test_rag_recall_question_id",
    #             'request_id': time.time()
    #         },
    #         query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
    #         credible='false', auto_router_source='false',
    #         query_reinforce=False, similarity_config={
    #             "method": 'llm',  # base/llm/rerank
    #             "is_filter": True,
    #             "simi_bar": 0.6,
    #             "model_name": 'gpt-4o',
    #             "top_n": 30
    #         },
    #         min_num_chunks=0
    #     )
    #     my_rag_recall3 = RagRecall(
    #         user_info={
    #             'application': 'GraTAG',
    #             'session_id': "test_rag_recall_session_id",
    #             'question_id': "test_rag_recall_question_id",
    #             'request_id': time.time()
    #         },
    #         query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
    #         credible='false', auto_router_source='false',
    #         query_reinforce=False, similarity_config={
    #             "method": 'rerank-sft',  # base/llm/rerank
    #             "is_filter": True,
    #             "simi_bar": 0.5,
    #             "model_name": 'gpt-4o',
    #             "top_n": 30
    #         },
    #         min_num_chunks=0
    #     )
    #
    #     my_rag_recall4 = RagRecall(
    #         user_info={
    #             'application': 'GraTAG',
    #             'session_id': "test_rag_recall_session_id",
    #             'question_id': "test_rag_recall_question_id",
    #             'request_id': time.time()
    #         },
    #         query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
    #         credible='false', auto_router_source='false',
    #         query_reinforce=False, similarity_config={
    #             "method": 'rerank_base',  # base/llm/rerank
    #             "is_filter": False,
    #             "simi_bar": 0.6,
    #             "model_name": 'gpt-4o',
    #             "top_n": 30
    #         },
    #         min_num_chunks=0
    #     )
    #
    #     my_rag_recall5 = RagRecall(
    #         user_info={
    #             'application': 'GraTAG',
    #             'session_id': "test_rag_recall_session_id",
    #             'question_id': "test_rag_recall_question_id",
    #             'request_id': time.time()
    #         },
    #         query=test_query_i, logger=log, search_field=copy.deepcopy(search_field),
    #         credible='false', auto_router_source='false',
    #         query_reinforce=False, similarity_config={
    #             "method": 'rerank-sft-0829',  # base/llm/rerank/rerank_base
    #             "is_filter": True,
    #             "simi_bar": 0.8,
    #             "model_name": 'gpt-4o',
    #             "top_n": 30
    #         },
    #         min_num_chunks=5
    #     )
    #
    #     # # 大模型过滤版
    #     # try:
    #     #     init_time = time.time()
    #     #     my_rag_recall1.call_chunk_rank(copy.deepcopy(chunks))
    #     #     data_base_i = my_rag_recall1.get_data_base()
    #     #     res_dict = {
    #     #         "test_query_i": test_query_i,
    #     #         "sorted_sources": data_base_i['use_for_check_items'],
    #     #         "time": time.time() - init_time
    #     #     }
    #     #     res_dict.update(test_query_i_dict)
    #     #     all_base_results_base.append(res_dict)
    #     # except:
    #     #     print("fail")
    #     #
    #     # # 大模型过滤版
    #     # try:
    #     #     init_time = time.time()
    #     #     my_rag_recall2.call_chunk_rank(copy.deepcopy(chunks))
    #     #     data_base_i = my_rag_recall2.get_data_base()
    #     #     res_dict = {
    #     #         "test_query_i": test_query_i,
    #     #         "sorted_sources": data_base_i['use_for_check_items'],
    #     #         "time": time.time() - init_time
    #     #     }
    #     #     res_dict.update(test_query_i_dict)
    #     #     all_base_results_base_llm_filter_gpt_4o.append(res_dict)
    #     # except:
    #     #     print("fail")
    #     #
    #     # # rerank版
    #     # try:
    #     #     init_time = time.time()
    #     #     my_rag_recall3.call_chunk_rank(copy.deepcopy(chunks))
    #     #     data_base_i = my_rag_recall3.get_data_base()
    #     #     res_dict = {
    #     #         "test_query_i": test_query_i,
    #     #         "sorted_sources": data_base_i['use_for_check_items'],
    #     #         "time": time.time() - init_time
    #     #     }
    #     #     res_dict.update(test_query_i_dict)
    #     #     all_base_results_rerank_sft.append(res_dict)
    #     # except:
    #     #     print("fail")
    #     #
    #     # # rerank_base版
    #     # try:
    #     #     init_time = time.time()
    #     #     my_rag_recall4.call_chunk_rank(copy.deepcopy(chunks))
    #     #     data_base_i = my_rag_recall4.get_data_base()
    #     #     res_dict = {
    #     #         "test_query_i": test_query_i,
    #     #         "sorted_sources": data_base_i['use_for_check_items'],
    #     #         "time": time.time() - init_time
    #     #     }
    #     #     res_dict.update(test_query_i_dict)
    #     #     all_base_results_rerank_base.append(res_dict)
    #     # except:
    #     #     print("fail")
    #
    #     # rerank_0828版
    #     try:
    #         init_time = time.time()
    #         my_rag_recall5.call_chunk_rank(copy.deepcopy(chunks))
    #         data_base_i = my_rag_recall5.get_data_base()
    #         res_dict = {
    #             "test_query_i": test_query_i,
    #             "sorted_sources": data_base_i['use_for_check_items'],
    #             "time": time.time() - init_time
    #         }
    #         res_dict.update(test_query_i_dict)
    #         all_base_results_rerank_0829_sft_all_old_database.append(res_dict)
    #     except:
    #         print("fail")
    #
    #     # with open("0826_all_base_results_base.json", 'w', encoding="utf-8") as f:
    #     #     json.dump(all_base_results_base, f, indent=4, ensure_ascii=False)
    #     # with open("0826_all_base_results_base_llm_filter_gpt_4o.json", 'w', encoding="utf-8") as f:
    #     #     json.dump(all_base_results_base_llm_filter_gpt_4o, f, indent=4, ensure_ascii=False)
    #     # with open("0826_all_base_results_rerank_sft.json", 'w', encoding="utf-8") as f:
    #     #     json.dump(all_base_results_rerank_sft, f, indent=4, ensure_ascii=False)
    #     # with open("0826_all_base_results_rerank_base.json", 'w', encoding="utf-8") as f:
    #     #     json.dump(all_base_results_rerank_base, f, indent=4, ensure_ascii=False)
    #     with open("rag_evaluation/0826_all_base_results_rerank_sft_0829_all_old_database.json", 'w', encoding="utf-8") as f:
    #         json.dump(all_base_results_rerank_0829_sft_all_old_database, f, indent=4, ensure_ascii=False)
