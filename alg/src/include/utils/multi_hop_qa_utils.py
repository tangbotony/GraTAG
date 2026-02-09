import re
from include.utils.text_utils import generate_random_string
from include.decorator import timer_decorator


def get_chain_queries(multi_hop_qa_dag, multi_hop_sub_query):
    upqueries = multi_hop_qa_dag.print_infostream(multi_hop_sub_query)
    if upqueries:
        new_upqueries = []
        for upq in upqueries:
            if upq not in ['Start', 'End']:
                new_upqueries.append(upq)
        res = new_upqueries
    else:
        res = []
    return res

@timer_decorator
def get_multi_hop_sub_queries(query_turn, multi_hop_qa_dag):
    """
    对于给定的multi_hop_qa_dag，返回批量检索所需要的检索词，主要为了在一次并行检索内可以扩召回。
    在处理思维链中子问题时，检索词是带上了子问题的上游父节点问题的。

    params:
        input:
            query_turn: multi-hop-qa 返回的带并行条件的list
            multi_hop_qa_dag: multi-hop-qa类
        output:
            ref_queries: sub_query_with_chain_list
            ref_queries_dict: {origin_sub_query: sub_query_with_chain}

    """
    ref_queries = []
    ref_queries_dict = dict()
    for parallel_list in query_turn:
        for query_origin in parallel_list:
            if query_origin not in ref_queries:
                multi_hop_sub_query = get_chain_queries(multi_hop_qa_dag, query_origin)
                multi_hop_sub_query_chain = ' '.join(multi_hop_sub_query + [query_origin])
                ref_queries.append(multi_hop_sub_query_chain)
                ref_queries_dict[multi_hop_sub_query_chain] = query_origin

    res_list, res_dict = list(), dict()
    for ref_queries_i in ref_queries:
        query_origin = ref_queries_dict[ref_queries_i]
        ref_queries_keyword_i = multi_hop_qa_dag[query_origin].rag_query
        res_list.append(ref_queries_keyword_i)
        res_dict[query_origin] = ref_queries_keyword_i
    return res_list, res_dict


def set_multi_hop_sub_queries(query_turn, multi_hop_qa_dag, RagQAConfig):
    """
    对于给定的multi_hop_qa_dag，返回批量检索所需要的检索词，主要为了在一次并行检索内可以扩召回。
    在处理思维链中子问题时，检索词是带上了子问题的上游父节点问题的。

    params:
        input:
            query_turn: multi-hop-qa 返回的带并行条件的list
            multi_hop_qa_dag: multi-hop-qa类
        output:
            ref_queries: sub_query_with_chain_list
            ref_queries_dict: {origin_sub_query: sub_query_with_chain}

    """
    ref_queries = []
    ref_queries_dict = dict()
    for parallel_list in query_turn:
        for query_origin in parallel_list:
            if query_origin not in ref_queries:
                if RagQAConfig['EXP_CONFIG']['recall_rag'] == 'with_upstream':
                    multi_hop_sub_query = get_chain_queries(multi_hop_qa_dag, query_origin)
                else:
                    multi_hop_sub_query = []
                multi_hop_sub_query_chain = ' '.join(multi_hop_sub_query + [query_origin])
                ref_queries.append(multi_hop_sub_query_chain)
                ref_queries_dict[multi_hop_sub_query_chain] = query_origin

    # ref_queries_keyword = get_questions_keywords(
    #     ref_queries, RagQAConfig['TASK_MODEL_CONFIG']['question_keyword'])

    ref_queries_keyword = []
    for ref_query_i in ref_queries:
        # prompt = "请帮我提取在搜索网站上检索这些问题的简略搜索语句：\n{}\n注意：请直接给我检索语句，不要多余的话，对于多个问题的情况，不要简单的罗列问题而是给出综合的、简介有效适合检索的语句".format(
        #     ref_query_i)
        # model_name = RagQAConfig['TASK_MODEL_CONFIG']['get_baidu_query']
        # log.info(f"检索词生成 prompt:{prompt}, model:{model_name}")
        #
        # res = llm_call(
        #     query=prompt,
        #     model_name=model_name,
        #     n=1)
        # log.info("检索词生成 response:{}".format(res))
        ref_queries_keyword.append(ref_query_i)

    res_list, res_dict = list(), dict()
    for ref_queries_i, ref_queries_keyword_dict_i in zip(ref_queries, ref_queries_keyword):
        # ref_queries_keyword_i = ' '.join(ref_queries_keyword_dict_i['keywords'])
        ref_queries_keyword_i = ref_queries_keyword_dict_i
        res_list.append(ref_queries_keyword_i)
        query_origin = ref_queries_dict[ref_queries_i]
        res_dict[query_origin] = ref_queries_keyword_i
        multi_hop_qa_dag[query_origin].rag_query = ref_queries_keyword_i
    return res_list, res_dict


def get_chain_queries_qa(multi_hop_qa_dag, multi_hop_sub_query, fast):
    qa_chain = []
    qa_chain_reference = []
    for sub_query in multi_hop_sub_query:
        origin_answer = multi_hop_qa_dag[sub_query].answer['answer']
        # 正则表达式模式：匹配中括号内的8个字符
        pattern = r'\[[A-Za-z0-9]{8}\]'
        # 使用正则表达式的 `sub` 方法替换匹配的字符串为空字符串
        output_str = re.sub(pattern, '', origin_answer)
        qa_chain.append(
            {
                'Multi-hop-sub-question': sub_query,
                'Multi-hop-sub-answer': output_str
            }
        )
        if fast == 'true':
            description = '{}\n'.format(sub_query)
        else:
            description = '{}\n{}\n'.format(sub_query, output_str)
        key = generate_random_string(description, 8)
        qa_chain_reference.append(
            {
                'id': key,
                'description': description,
                'title': sub_query,
                'url': '',
                'theme': sub_query,
                'source': 'multi-hop',
                'source_id': '',
                'key': "[%s]" % key
            }
        )
    return qa_chain, qa_chain_reference
