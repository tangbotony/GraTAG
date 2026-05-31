import copy
import time
import concurrent.futures
import traceback
from include.context import RagQAContext, DocQAContext
from include.rag import RagRecall
from include.logger import ContextLogger
from include.utils.text_utils import get_md5, find_duplicates
from include.utils.Igraph_utils import IGraph, ArcNode
from include.context.reference_controller import ReferenceController
from include.utils.multi_hop_qa_utils import *
from include.query_intent_recognition import get_reinforced_qkw
from modules.query_division_based_cot_group import QueryDivisionBasedCoTTask
from include.utils.time_utils import TimeCounter
from include.config import CommonConfig, DocQAConfig, RagQAConfig
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
from include.decorator import timer_decorator
from include.logger import log


def special_score_for_direct_recall_source(data_base_i, num_summary=5):
    use_for_check_items = dict()
    for key, value in zip(list(data_base_i['use_for_check_items'].keys())[: num_summary],
                          list(data_base_i['use_for_check_items'].values())[:num_summary]):
        use_for_check_items[key] = value
    content_dict = dict()
    for key, value in zip(list(data_base_i['use_for_check_items_content_dic'].keys())[:num_summary],
                          list(data_base_i['use_for_check_items_content_dic'].values())[:num_summary]):
        content_dict[key] = value
    simi_dict = dict()
    for key, value in zip(list(data_base_i['use_for_check_items_opinion_similarity_dic'].keys())[: num_summary],
                          list(data_base_i['use_for_check_items_opinion_similarity_dic'].values())[:num_summary]):
        simi_dict[key] = value
    for item in use_for_check_items.values():
        item['rerank_score'] = 1.0
        item['other_info']['score'] = 1.0
    simi_dict = {key: {'': 1.0} for key in simi_dict.keys()}

    return (use_for_check_items,
            {'use_for_check_items': use_for_check_items,
             'use_for_check_items_content_dic': content_dict,
             'use_for_check_items_opinion_similarity_dic': simi_dict})


class RecallTask:
    """ 检索召回
    必传入参`
        session_id = context.get_session_id()
        request_id = context.get_request_id()
        question_id = context.get_question_id()
        question = context.get_question()

    获取本模块执行结果
    """
    def __init__(self, rag_qa_context: RagQAContext, module_name: str = ''):
        self.module_name = "RagRecallTask"
        self.context = rag_qa_context
        self.QAConfig = RagQAConfig
        if type(self.context) is RagQAContext:
            self.QAConfig = RagQAConfig
        elif type(self.context) is DocQAContext:
            self.QAConfig = DocQAConfig
        
        if rag_qa_context.get_retrieval_field():
            self.retrieval_field = rag_qa_context.get_retrieval_field()
        else:
            self.retrieval_field = {
                'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])
            }
        # time related
        self._time = TimeCounter()
        self._time_task_name = self.module_name
        self._time.add_task(self._time_task_name)
        self._time.add_time_stone(self._time_task_name, "startRagRecallTask")

        self._word_list = ['今天', '今天', '今日', '明天', '明日', '昨天', '昨日', '前天', '后天', '年', '月', '日',
                           '上周', '上一周', '本周', '这周', '这一周', '本月', '这个月', '上个月', '新闻', '有', '什么', '的']

    def _router(self, search_field, origin_query):
        """
            检索方式分发，对于不同的query，指定不同的数据源
        """
        news_type = 0
        if 'iaar_database_kwargs' in search_field:
            try:
                body = search_field['iaar_database_kwargs']
                route = body['online_search'] if 'online_search' in body else body
                # 触发榜单检索 在有明确起止日期的情况下，都可以通过榜单通道来直接获取这段日期内的材料
                chinese_query = re.sub(r'[^\u4e00-\u9fa5]', '', origin_query)
                for word in self._word_list:
                    chinese_query = chinese_query.replace(word, '')
                if len(chinese_query) <= 1 and 'start_date' in route:
                    log.debug("触发榜单检索!!!")
                    news_type = 'hot_news'
                # 触发新闻检索
                elif "新闻" in origin_query and "keywords" in body:
                    log.debug("触发新闻检索!!!")
                    news_type = 'news'
            except:
                traceback.print_exc()
        elif 'file_database_kwargs' in search_field:
            assert type(self.context) is DocQAContext, "type(self.context) is DocQAContext!!!"
            body = search_field['file_database_kwargs']
            body["doc_id"] = self.context.get_single_question().get_pdf_ids()
            body['pro_flag'] = self.context.get_single_question().get_pro_flag()
        return news_type

    @timer_decorator
    def get_graph_recall(self, graph: IGraph, application: str = 'QuestionAnswer',
                         retrieval_field=None, top_n_indices: int = 64):
        self._time.add_time_stone(self._time_task_name, "get_graph_recall")
        ContextLogger(self.context).info("start get_graph_recall")
        # 变量合法声明
        ContextLogger(self.context).info("start assertion")
        self._assertion(graph, retrieval_field, application)

        # 添加检索范围
        ContextLogger(self.context).info("start add retrieval_range")
        self._add_retrieval_range()

        # 路由检索域
        ContextLogger(self.context).info("start router")
        news_type = self._router(self.retrieval_field, self.context.get_origin_question())

        # 获取思维链图上需要检索的词，由于可能需要针对多跳思维链进行改写、考虑上下链的query等需求，所以可能用于检索的词不等于思维链问题
        ContextLogger(self.context).info("start get_recall_queries")
        ref_query, origin_query_2_ref_query = self._get_recall_queries(graph, application)
        if self.QAConfig['EXP_CONFIG']['add_ref_to_final_answer_mode'] in ['ori_query_ref', 'all_ref']:
            if news_type in ['hot_news', 'news']:
                if self.context.get_origin_question() not in ref_query:
                    ref_query.append(self.context.get_origin_question())
                    origin_query_2_ref_query[self.context.get_question()] = self.context.get_origin_question()
            else:
                if self.context.get_question() not in ref_query:
                    ref_query.append(self.context.get_question())
                    origin_query_2_ref_query[self.context.get_question()] = self.context.get_question()
        ContextLogger(self.context).warning(
            "时间窗写入检索器，app={}, 参与检索的query={}, 检索范围:{}, len dialog={}".format(
                application, ref_query,
                self.retrieval_field, len(self.context.get_dialog().items())))

        # 开始多路检索
        ContextLogger(self.context).info("start multi-source RagRecall")
        reference_controller = ReferenceController()

        all_list = []
        unique_ref = set()
        all_ref_dict = {}

        def process_query(query_i, retrieval_field=None, pro_flag=None):
            if not retrieval_field:
                retrieval_field = copy.deepcopy(self.retrieval_field)
            if pro_flag is None:
                pro_flag = self.context.get_single_question().get_pro_flag()
            # step1 检索
            rag_recall_i = RagRecall(
                user_info={
                    'application': application,
                    'session_id': self.context.get_session_id(),
                    'question_id': self.context.get_question_id(),
                    'request_id': self.context.get_request_id(),
                    'user_id': self.context.get_user_id()
                },
                query=query_i, logger=ContextLogger(self.context), search_field=retrieval_field,
                credible=False, auto_router_source=False if news_type in ['hot_news', 'news'] else True,
                query_reinforce=True if self.QAConfig['EXP_CONFIG']['is_reinforce'] == 'true' else False,
                retrieval_range=self.context.get_retrieval_range(),
                similarity_config=self.QAConfig['RAG_CONFIG']['similarity_config'],
                chunk_min_length=self.QAConfig['RAG_CONFIG']['chunk_min_length'],
                max_chunk=self.QAConfig['RAG_CONFIG']['max_chunk'],
                # retrieval_range=None,  # 指定的检索词
                # auto_retrieval_range=True,  # 自动为query添加识别检索区间
                pro_flag=pro_flag,
                use_raw_ranker=self.QAConfig['RAG_CONFIG']['raw_ranker']
            )
            rag_recall_i.construct_database()
            data_base_i = rag_recall_i.get_data_base()
            fig_data_base_i = rag_recall_i.get_images_data_base()

            # 最终被分发到的材料
            final_chosen_ref_i = data_base_i['use_for_check_items']
            if not pro_flag and self.context.get_single_question().get_pro_flag() and 'iaar_database_kwargs' in self.retrieval_field:
                final_chosen_ref_i, data_base_i = special_score_for_direct_recall_source(data_base_i)
            # 将检索回的资料挂载到graph图上
            for key, value in origin_query_2_ref_query.items():
                if value == query_i:
                    origin_sub_query_i = key
                    if origin_sub_query_i not in [self.context.get_origin_question(), self.context.get_question()]:
                        graph.add_node_param(origin_sub_query_i, "reference", [], attr_type="list")
                        graph[origin_sub_query_i].reference = copy.deepcopy(final_chosen_ref_i)
                    else:
                        ContextLogger(self.context).info("query_i {} not in graph".format(query_i))
                    if origin_sub_query_i not in all_ref_dict:
                        all_ref_dict[origin_sub_query_i] = 0
                    all_ref_dict[origin_sub_query_i] += len(final_chosen_ref_i)
            return data_base_i, fig_data_base_i, query_i, final_chosen_ref_i

        log.info("ref_query:{}".format(ref_query))
        unique_doc_id = set()
        with concurrent.futures.ThreadPoolExecutor(self.QAConfig['RAG_CONFIG']['parallel']) as executor:
            # 使用列表推导式提交任务并收集结果
            futures = [executor.submit(process_query, query_i) for query_i in ref_query]
            # 需要互联网检索时，补充直接检索这一通路
            if self.context.get_single_question().get_pro_flag() and 'iaar_database_kwargs' in self.retrieval_field:
                futures.append(executor.submit(
                    process_query, self.context.get_question(),
                    retrieval_field={
                        'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param_pro_flag'])
                    }, pro_flag=False))
                ContextLogger(self.context).warning(
                    "补充检索，app={}, 参与检索的query={}, 检索范围:{}, len dialog={}".format(
                        application, self.context.get_question(),
                        {
                            'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param_pro_flag'])
                        }, len(self.context.get_dialog().items())))
            for future in concurrent.futures.as_completed(futures):
                references_i, fig_i, query_i, final_chosen_ref_i = future.result()
                try:
                    if query_i in [self.context.get_question(), self.context.get_origin_question()]:
                        reference_controller.set_origin_ref(final_chosen_ref_i)
                    reference_controller.add(references_i)
                    reference_controller.add_fig(fig_i, application)
                    new_list = []
                    for ref in final_chosen_ref_i.values():
                        new_list.append(ref['description'])
                        unique_ref.add(ref['description'])
                        unique_doc_id.add(ref['other_info']['doc_id'])
                    all_list.extend(new_list)
                except:
                    log.error(traceback.format_exc())

        # 找到重复元素
        duplicates = find_duplicates(all_list)
        ContextLogger(self.context).info(
            "\n application是：{}, 共{}个图片, 共{}个reference，{}个不同的reference, 分布是：{}, 重复的reference个数: {}".format(
                application, len(reference_controller.get_fig(application)), len(all_list), len(unique_ref),
                all_ref_dict, len(duplicates)))
        time_duration = self._time.time_since_specific_stone(self._time_task_name, "get_graph_recall")
        ContextLogger(self.context).info("In RagRecall, total {}s".format(time_duration))
        if application in ['QuestionAnswer', 'DocAnswer']:
            self.context.add_references_result(reference_controller.get_all())
            self.context.set_origin_ref(reference_controller.get_origin_ref())
            self.context.set_recall_finished_flag(True)
        self.context.add_fig_result(reference_controller.get_fig(application), application)
        return {
            "is_success": True,
            "return_code": "",
            "detail": "",
            "timestamp": "",
            "err_msg": ""
        }

    @timer_decorator
    def _get_rag_query(self, query):
        # 增强的问题
        rag_queries = [query]
        if self.QAConfig['EXP_CONFIG']['is_reinforce'] == 'true':
            reinforced_questions = self.context.get_reinforced_questions()
            if not reinforced_questions:
                reinforced_questions = get_reinforced_qkw(query)
            if reinforced_questions:
                for reinforced_question in reinforced_questions:
                    rag_queries.append(reinforced_question['question'])

        simi_queries = [query]

        ContextLogger(self.context).info("*******Time for get_rag_query*******: {}".format(
            self._time.add_time_stone(self._time_task_name, "get_rag_query")))

        rag_queries = list(set(rag_queries))[:5]
        return rag_queries, simi_queries

    def _add_retrieval_range(self):
        try:
            for retrieval_field_name, retrieval_field_kwargs in self.retrieval_field.items():
                if retrieval_field_name == 'iaar_database_kwargs':
                    retrieval_field_kwargs['request_id'] = self.context.get_session_id()
                    if RagQAConfig['EXP_CONFIG']['is_retrieval_range'] == 'true':
                        # 嵌入关键词
                        retrieval_range = self.context.get_retrieval_range()
                        if 'keywords' in retrieval_range and len(retrieval_range['keywords']) > 0:
                            retrieval_field_kwargs['keywords'] = ' '.join(retrieval_range['keywords'])

                        # 嵌入时间窗
                        route = retrieval_field_kwargs['online_search'] if 'online_search' in retrieval_field_kwargs else retrieval_field_kwargs
                        tm_range = self.context.get_retrieval_range()
                        if 'start_time' in tm_range and 'end_time' in tm_range and len(tm_range['start_time']) > 0 and len(tm_range['end_time']) > 0:
                            route['start_date'] = tm_range['start_time']
                            route['end_date'] = tm_range['end_time']
        except:
            traceback.print_exc()

    def _assertion(self, graph, retrieval_field, application):
        assert isinstance(graph, IGraph), ContextLogger(self.context).error("传入的graph 是一个IGraph类")
        assert self.context.get_session_id() is not None, ContextLogger(self.context).error("session_id为空")
        assert self.context.get_request_id() is not None, ContextLogger(self.context).error("request_id为空")
        assert self.context.get_question_id() is not None, ContextLogger(self.context).error("question_id为空")
        assert application in ['QuestionAnswer', 'Timeline', 'DocAnswer'], \
            ContextLogger(self.context).error("application in ['QuestionAnswer', 'Timeline', 'DocAnswer']")
        assert self.context.get_question() is not None and len(self.context.get_question()) != 0, \
            ContextLogger(self.context).error("question为空")
        if retrieval_field:
            self.retrieval_field = retrieval_field
        assert isinstance(self.retrieval_field, dict), "retrieval_field 格式错误！"
        assert len(self.retrieval_field.keys()) > 0, "未指定有效的检索源！"

    def _get_recall_queries(self, graph, application):
        """
            input:
                graph: 思维链图
                application: 检索应用
            returns:
                ref_query: 所有需要检索的词
                origin_query_2_ref_query: 原graph节点的子问题到检索词的映射（包括原问题）

        """
        graph_node_turn, graph_query_turn, graph_final = graph.get_turns()
        ContextLogger(self.context).info("\n application是：{}, 思维链是：{}".format(application, graph_query_turn))
        ref_query, origin_query_2_ref_query = set_multi_hop_sub_queries(graph_query_turn, graph, self.QAConfig)  # 替换思维链
        if self.QAConfig['EXP_CONFIG']['add_ref_to_final_answer_mode'] in ['ori_query_ref', 'all_ref']:
            ref_query.append(self.context.get_question())
            origin_query_2_ref_query[self.context.get_question()] = self.context.get_question()
        ref_query = list(set(ref_query))  # 去重
        # 确保待检索的词都在origin_query_2_ref_query中
        for ref_query_i in ref_query:
            assert ref_query_i in list(origin_query_2_ref_query.values()), \
                "query_i in list(origin_query_2_ref_query.values())"
        return ref_query, origin_query_2_ref_query



if __name__ == '__main__':
    import time
    from include.utils.skywalking_utils import trace_new, start_sw
    start_sw()

    test_question_list = [
        "今天安徽怀远发生了什么？"
    ]
    for i, query_i in enumerate(test_question_list[:1]):
        session_idx = "mock_session_{}".format(i)
        context = RagQAContext(session_id=get_md5(session_idx), user_id="mock_user_id")
        context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                    question_id=get_md5("{}_qe".format(session_idx)), question=test_question_list[i])
        context.set_basic_user_info({"User_Date": time.time(), "User_IP": '39.99.228.188'})
        context.set_retrieval_field({
            'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])
        })
        cot = QueryDivisionBasedCoTTask(context).get_cot(use_scene="general", if_parallel=True, split_num_threshold=3)
        dag = context.get_dag()
        node_turn, query_turn, final = dag.get_turns()

        application = 'QuestionAnswer'

        response_graph = RecallTask(context).get_graph_recall(dag, application)
        references_doc = context.get_references_result_doc()
        ref_answer = context.get_ref_answer()
        ref_fig = context.get_fig_result(application)
        print("context.ref_answer:{}".format(ref_answer))










