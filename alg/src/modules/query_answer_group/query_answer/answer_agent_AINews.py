# coding:utf-8
# Answer Generation
import copy
import random
import datetime
import concurrent.futures
import traceback

from include.logger import log
from include.logger import ContextLogger
from include.context import RagQAContext
from include.rag.rag_recall_agent import RagRecall
from include.query_intent_recognition import get_reinforced_qkw
from modules.query_division_based_cot_group import QueryDivisionBasedCoTTask
from include.rag.choose_top_ref import get_reference, get_reference_balanced_v2
from include.utils.Igraph_utils import IGraph
from include.utils.multi_hop_qa_utils import set_multi_hop_sub_queries, get_multi_hop_sub_queries, get_chain_queries_qa
from include.decorator import timer_decorator
from modules.query_answer_group.query_answer.answer_agent import DocAnswer


class DocAnswerAINews(DocAnswer):
    def __init__(
            self,
            question: str,
            references: dict,
            multi_hop_qa_dag: IGraph = None,
            max_try: int = 5,
            candidate_images: list = None,
            context=None
    ):
        super().__init__(question, references, multi_hop_qa_dag, max_try, candidate_images, context)
        self.name = "DocAnswerAINews"
        self._max_input_tokens = self.QAConfig['EXP_CONFIG']['context_length']

    @timer_decorator
    def _call_single_hop_answer(self, streaming=False):
        message = ""

        use_for_check_items_internet = self._references["use_for_check_items"]
        use_for_check_items_content_dic_internet = self._references["use_for_check_items_content_dic"]
        use_for_check_items_opinion_similarity_dic_internet = self._references[
            "use_for_check_items_opinion_similarity_dic"]

        _, _, ref_str_item_info_internet = get_reference(
            use_for_check_items_internet, use_for_check_items_opinion_similarity_dic_internet,
            use_for_check_items_content_dic_internet, [self._question], mode=self.name
        )
        return self._single_answer(self._question, ref_str_item_info_internet, message,
                                   mode='query_simple_answer', streaming=streaming, add_title=True)

    @timer_decorator
    def _call_multi_hop_answer(self, streaming=False):
        chain_results = {}
        message = ""

        use_for_check_items_internet_all = self._references["use_for_check_items"]
        use_for_check_items_content_dic_internet_all = self._references["use_for_check_items_content_dic"]
        use_for_check_items_opinion_similarity_dic_internet_all = self._references[
            "use_for_check_items_opinion_similarity_dic"]

        node_turn, query_turn, final = self._multi_hop_qa_dag.get_turns()
        ref_query, origin_query_2_ref_query = get_multi_hop_sub_queries(query_turn, self._multi_hop_qa_dag)
        if self.QAConfig['EXP_CONFIG']['add_ref_to_final_answer_mode'] in ['ori_query_ref', 'all_ref']:
            ref_query.append(self.context.get_question())
            origin_query_2_ref_query[self.context.get_question()] = self.context.get_question()

        chain_results['chain'] = query_turn
        ContextLogger(self.context).info("\n 思维链结果：{}".format(
            query_turn
        ))

        query_pairs = self._multi_hop_qa_dag.print_relation()
        multi_hop_qa_end_queries = []
        for query_pair_i in query_pairs:
            if query_pair_i[1] == 'End' and query_pair_i[0] not in multi_hop_qa_end_queries:
                multi_hop_qa_end_queries.append(query_pair_i[0])

        balance_input_graph = dict()
        for sub_query in origin_query_2_ref_query.keys():
            if sub_query not in [self.context.get_question(), self.context.get_origin_question()]:
                balance_input_graph[sub_query] = self._multi_hop_qa_dag[sub_query].reference
            else:
                balance_input_graph[sub_query] = self.context.get_origin_ref()

        ref_multi_hop_list = balance_input_graph

        ref_multi_hop_list = get_reference_balanced_v2(
            use_for_check_items_internet_all, use_for_check_items_opinion_similarity_dic_internet_all,
            use_for_check_items_content_dic_internet_all, ref_query, top_n_indices=self._top_n_indices, graph=balance_input_graph,
            origin_query_2_ref_query=origin_query_2_ref_query, mode=self.name
        )

        chain_results['sub_query'] = []
        if not self.context.get_QA_quickpass():   # 非速通版本，解答子问题
            for query_turn_parallel_list in query_turn:
                try:
                    def process_source(sub_query):
                        sub_query_answer = self._get_sub_query(
                            sub_query, origin_query_2_ref_query, ref_multi_hop_list, add_title=True)
                        return {
                            "sub_query_answer": sub_query_answer,
                            "sub_query": sub_query
                        }

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # 使用列表推导式提交任务并收集结果
                        futures = [executor.submit(process_source, sub_query) for sub_query in query_turn_parallel_list]

                        for future in concurrent.futures.as_completed(futures):
                            ans_sub_query_res = future.result()
                            sub_query_i = ans_sub_query_res['sub_query']
                            ans_sub_query_i = ans_sub_query_res['sub_query_answer']
                            self._multi_hop_qa_dag[sub_query_i].answer = ans_sub_query_i
                            chain_results['sub_query'].append(copy.deepcopy(ans_sub_query_i))
                except:
                    traceback.print_exc()
        else:
            ContextLogger(self.context).info("您选用的是速通版本解答，因此会提供fake子问题记录，但并不会影响最终输出。")
            for query_turn_parallel_list in query_turn:
                def process_source(sub_query):
                    sub_query_answer = {
                        'answer': '',
                        'input_llm': '',
                        'message': 'QuickPass mode',
                        'output_llm': '',
                        'reference': '',
                        'source': 'QuickPass SubQAAnswer',
                        'valid': True}
                    return {
                        "sub_query_answer": sub_query_answer,
                        "sub_query": sub_query
                    }

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # 使用列表推导式提交任务并收集结果
                    futures = [executor.submit(process_source, sub_query) for sub_query in query_turn_parallel_list]

                    for future in concurrent.futures.as_completed(futures):
                        ans_sub_query_res = future.result()
                        sub_query_i = ans_sub_query_res['sub_query']
                        ans_sub_query_i = ans_sub_query_res['sub_query_answer']
                        self._multi_hop_qa_dag[sub_query_i].answer = ans_sub_query_i
                        chain_results['sub_query'].append(copy.deepcopy(ans_sub_query_i))

        all_qa, all_qa_chain_reference = get_chain_queries_qa(
            self._multi_hop_qa_dag, multi_hop_qa_end_queries, fast=self.QAConfig['EXP_CONFIG']['is_fast'])
        ref_str_sub_query_i = copy.deepcopy(all_qa_chain_reference)
        if self.QAConfig['EXP_CONFIG']['add_ref_to_final_answer_mode'] in ['ori_query_ref', 'all_ref']:
            ref_str_sub_query_i = self.get_addition_ref(ref_str_sub_query_i, all_qa_chain_reference,
                                                        origin_query_2_ref_query, ref_multi_hop_list, chain_results)
        # 最终回答采用速通或非速通模板
        if self.context.get_QA_quickpass():
            final_answer_mode = "query_answer_quickpass"
        else:
            final_answer_mode = "query_answer"
            
        if streaming:
            return self._single_answer(
                self._question, ref_str_sub_query_i, message, mode=final_answer_mode, streaming=streaming, add_title=True)
        else:
            final_answer = self._single_answer(
                self._question, ref_str_sub_query_i, message, mode=final_answer_mode, streaming=streaming, add_title=True)
            chain_results['final_answer'] = copy.deepcopy(final_answer)
            final_answer['chain_results'] = chain_results
            return final_answer

    def get_addition_ref(self, ref_str_sub_query_i, all_qa_chain_reference, origin_query_2_ref_query,
                         ref_multi_hop_list, chain_results):
        # 维持一个已有的reference库，避免重复
        addition_ref_set = set()

        # 子问题问答内容作为参考信息  这里不启用
        for qa_ref in all_qa_chain_reference:
            if qa_ref['description'] not in addition_ref_set:
                addition_ref_set.add(qa_ref['description'])

        # ori_query_ref的部分
        sub_ref_query = origin_query_2_ref_query[self._question]
        if sub_ref_query in ref_multi_hop_list:
            _, _, ref_str_sub_query_i_ref = ref_multi_hop_list[sub_ref_query]
            sub_ref_query_ref_list = []
            for ref_detail_i in ref_str_sub_query_i_ref:
                if ref_detail_i['description'] not in addition_ref_set:
                    sub_ref_query_ref_list.append(ref_detail_i)
                    addition_ref_set.add(ref_detail_i['description'])
        else:
            sub_ref_query_ref_list = []
        ref_str_sub_query_i = copy.deepcopy(sub_ref_query_ref_list)

        # sub_query_ref的部分
        if self.context.get_QA_quickpass():
            final_answer_mode = "query_answer_quickpass"
        else:
            final_answer_mode = "query_answer"
        if self.QAConfig['EXP_CONFIG']['add_ref_to_final_answer_mode'] in ['all_ref']:
            if final_answer_mode == "query_answer":
                description_set = set()
                sub_ref_query_ref_list = []
                for sub_ref_query_dict_i in chain_results['sub_query']:
                    # 获取所有需要新增的reference
                    if isinstance(sub_ref_query_dict_i['reference'], dict):
                        for ref_i_key, ref_i_value in sub_ref_query_dict_i['reference'].items():
                            if ref_i_value['description'] not in addition_ref_set:
                                description_set.add(ref_i_value['description'])
                    else:
                        ContextLogger(self.context).info("\n sub_ref_query_dict_i: {}".format(
                            sub_ref_query_dict_i
                        ))
                for query_ref_all_info in ref_multi_hop_list.values():
                    for query_ref_i in query_ref_all_info[2]:
                        if (query_ref_i['description'] in description_set and
                                query_ref_i['description'] not in addition_ref_set):
                            sub_ref_query_ref_list.append(query_ref_i)
                            addition_ref_set.add(query_ref_i['description'])

            elif final_answer_mode == "query_answer_quickpass":
                description_set = set()
                sub_ref_query_ref_list = []
                for sub_query_i, sub_query_ref_i in ref_multi_hop_list.items():
                    sub_ref_query_dict_i, _, _ = sub_query_ref_i
                    # 获取所有需要新增的reference
                    if isinstance(sub_ref_query_dict_i, dict):
                        for ref_i_key, ref_i_value in sub_ref_query_dict_i.items():
                            if ref_i_value['description'] not in addition_ref_set:
                                description_set.add(ref_i_value['description'])
                    else:
                        ContextLogger(self.context).info("\n sub_ref_query_dict_i: {}".format(
                            sub_ref_query_dict_i
                        ))
                for query_ref_all_info in ref_multi_hop_list.values():
                    for query_ref_i in query_ref_all_info[2]:
                        if (query_ref_i['description'] in description_set and
                                query_ref_i['description'] not in addition_ref_set):
                            sub_ref_query_ref_list.append(query_ref_i)
                            addition_ref_set.add(query_ref_i['description'])
                if "PDFDocAnswer" not in self.name:
                    random.shuffle(sub_ref_query_ref_list)

            ref_str_sub_query_i = copy.deepcopy(ref_str_sub_query_i + sub_ref_query_ref_list)
        ContextLogger(self.context).info("\n Final Answer中共有{}个reference".format(
            len(ref_str_sub_query_i)
        ))
        return ref_str_sub_query_i


if __name__ == '__main__':
    import time
    from include.utils.skywalking_utils import trace_new, start_sw
    from include.config import RagQAConfig
    start_sw()

    init_time = time.time()
    question = '讨论在全球化背景下，“一带一路”倡议如何平衡政府与市场的作用，实现高质量的可持续发展。'
    session_id = 'Education'
    rag_qa_context = RagQAContext(session_id=session_id)
    rag_qa_context.add_single_question(datetime.datetime.now(), datetime.datetime.now(), question)
    rag_qa_context.set_basic_user_info({"User_Date": '123456', "User_IP": '39.99.228.188'})
    cot = QueryDivisionBasedCoTTask(rag_qa_context).get_cot(use_scene="general", if_parallel=True, split_num_threshold=3)
    multi_hop_rag_dag = rag_qa_context.get_dag()

    rag_qa_context.set_multi_hop_rag_queries(multi_hop_rag_dag)
    multi_hop_rag_dag_queries = []
    if multi_hop_rag_dag:
        node_turn, query_turn, final = multi_hop_rag_dag.get_turns()
        multi_hop_sub_query, _ = set_multi_hop_sub_queries(query_turn, multi_hop_rag_dag, RagQAConfig)
        for multi_hop_query_i in multi_hop_sub_query:
            if multi_hop_query_i not in multi_hop_rag_dag_queries:
                multi_hop_rag_dag_queries.append(multi_hop_query_i)
        log.warning("multi-hop is: {}".format(query_turn))
        rag_qa_context.set_multi_hop_rag_queries(multi_hop_rag_dag)
    log.info("\n multi_hop_rag_dag_queries: {}".format(multi_hop_rag_dag_queries))

    queries_response = get_reinforced_qkw(question)
    queries = [question]
    if queries_response:
        for response_i in queries_response:
            # if " ".join(response_i['keywords']) not in queries and len(queries) <= 10:
            #     queries.append(" ".join(response_i['keywords']))
            if response_i['question'] not in queries and len(queries) <= 8:
                queries.append(response_i['question'])

    queries = copy.deepcopy(queries) + multi_hop_rag_dag_queries
    simi_queries = copy.deepcopy(queries) + multi_hop_rag_dag_queries

    search_field = {
        # 'net_kwargs': {'max_entries': 20, 'mode': 'default', 'get_content': 30, 'timeout': 300, 'search_type': '',
        #                'is_filter': False},
        'iaar_database_kwargs': {'return_num': 100},
    }

    # 初始化证据召回模块
    my_rag_recall = RagRecall(
        search_field=search_field
    )
    # 向量召回
    my_rag_recall.construct_database(queries, simi_queries=simi_queries, key_query=question)
    references = my_rag_recall.get_data_base()
    figures = my_rag_recall.get_images_data_base()

    rag_qa_context.add_references_result(references)
    rag_qa_context.add_fig_result(figures, application='QuestionAnswer')
    references = rag_qa_context.get_references_result()
    figures = rag_qa_context.get_fig_result(application='QuestionAnswer')

    doc_answer = DocAnswerAINews(
        question=question, references=references,
        multi_hop_qa_dag=rag_qa_context.get_multi_hop_rag_queries(),
        candidate_images=figures,
        context=rag_qa_context
    )
    answer = doc_answer.query_answer(single_hop=True, streaming=True)
    for ans_i in answer:
        if isinstance(ans_i, str):
            print(ans_i, end="")
        elif isinstance(ans_i, dict):
            print("IMAGE: id: {}, url: {}".format(ans_i['data'][-1]['id'], ans_i['data'][-1]['url']))
    log.info("\n answer is: {}".format(answer))

    print("total_time is: ", time.time() - init_time)







