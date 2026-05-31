import json
import copy
import re
import time
import traceback
from include.context import RagQAContext, DocQAContext
from include.logger import ContextLogger
from include.utils.text_utils import get_md5
from include.utils.Igraph_utils import IGraph
from modules.query_division_based_cot_group import QueryDivisionBasedCoTTask
from include.utils.add_ref_to_doc import add_references_to_doc
from modules.query_answer_group.query_answer.multi_round_answer_agent import MultiRoundRagAnswer
from include.decorator import timer_decorator
from include.utils.call_white_list import search_whitelist
from include.config import CommonConfig, RagQAConfig, DocQAConfig

IAAR_DataBase_config = CommonConfig['IAAR_DataBase']


class QueryAnswerTask:
    """ 多轮引证回答
        必传入参`
            session_id = context.get_session_id()
            request_id = context.get_request_id()
            question_id = context.get_question_id()
            question = context.get_question()

        获取本模块执行结果
        接口请求参数
        RagQAContext:
            self._session_id string 会话id，用于标识同一个会话窗口内的问题
            self._dialog = {
                question_id: {
                    request_id string 单次请求的id（每请求一次接口都有一个独立的request_id）
                    question_id string 问题id
                    question string 用户输入问题
                    retrieval_range json（非必须）检索范围为用户前端修改后最终结果
                    {
                        "start_time": "xx",
                        "end_time": "xx",
                        "required_keywords": ["xx","xx",....],  # 包含全部关键词
                        "optional_keywords": ["xx","xx",....],  # 包含任意关键词
                        "required_character": ["xx", "xx", ....],   # 必须包含的人物（可以为空）
                        "required_location": ["xx", "xx", ....],   # 必须包含的地点 （可以为空）
                        "supplement": {}/{"description":"xx","choices":["xx", "xx", ....]}  # 问题补充用户确认结果
                    },
                    self._reference = ReferenceController()
                    self._multi_hop_rag_queries = IGraph()
                }
            }  # 会话历史
        """

    def __init__(self, qa_context: RagQAContext):
        self.context = qa_context
        if type(self.context) is RagQAContext:
            self.QAConfig = RagQAConfig
        elif type(self.context) is DocQAContext:
            self.QAConfig = DocQAConfig
        self.module_name = "QueryAnswerTask"


    @timer_decorator
    def get_query_answer(self, query, qa_series_id, qa_pair_collection_id, qa_pair_id, streaming=True):
        try:
            beginning_time = time.time()
            assert self.context.get_session_id() is not None, ContextLogger(self.context).error("请求session为空")
            assert self.context.get_request_id() is not None, ContextLogger(self.context).error("请求request_id为空")
            assert self.context.get_question_id() is not None, ContextLogger(self.context).error("请求question_id为空")
            assert self.context.get_question() is not None, ContextLogger(self.context).error("请求question为空")
            ContextLogger(self.context).info("Question is: {}".format(self.context.get_question()))

            # 白名单查询
            answer_generator = None
            ref_answer = None
            doc_answer = None
            if self.QAConfig["WHITE_LIST_CONFIG"]["is_use"] == 'true':
                try:
                    whitelist_response = search_whitelist(
                        scheme_id=self.QAConfig["WHITE_LIST_CONFIG"]["query_answer"]["scheme_id"],
                        input_info={"query": self.context.get_question()})
                    if whitelist_response is not None:
                        cache_result = whitelist_response[0]['output']
                        stream_info, ref_answer, ref_page = (cache_result['stream_info'],
                                                             cache_result['ref_answer'],
                                                             cache_result['ref_page'],)
                        # 将检索结束标置为True
                        self.context.set_recall_finished_flag(True)
                        ContextLogger(self.context).info(
                            "\n Get cache query_answer from white list success!!!")

                        def get_generator(stream_whitelist):
                            # 流式输出部分
                            complete_organize_state = {
                                "type": "state",
                                "data": "complete"
                            }
                            yield complete_organize_state

                            for answer_i in stream_whitelist:
                                if 'text' in answer_i.keys():
                                    # 输出文字
                                    for str_i in answer_i['text']:
                                        yield str_i
                                elif 'text-image' in answer_i.keys():
                                    # 输出图片位置
                                    yield answer_i['text-image']
                                elif 'image' in answer_i.keys():
                                    yield answer_i['image']

                        answer_generator = get_generator(stream_info)
                    else:
                        ContextLogger(self.context).info(
                            "\n There is not cache query_intent_recognition result in  white list. "
                            "get result from the beginning.")
                except:
                    ContextLogger(self.context).error(
                        traceback.format_exc())
                    ContextLogger(self.context).info(
                        "\n Get query_intent_recognition from white list occur error. get result from the beginning.")

            # 参考文件
            if not ref_answer:
                ref_answer = self.context.get_ref_answer()
            res = {
                "type": "ref_answer",
                "data": ref_answer,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id
            }
            yield f"data: {json.dumps(res, ensure_ascii=False)}\0".encode(errors="ignore")

            if not answer_generator:
                # assert "use_for_check_items" in self.context.get_references_result() and len(
                #     self.context.get_references_result()["use_for_check_items"]) > 0, ContextLogger(self.context).error(
                #     "传入的reference为空")

                ContextLogger(self.context).info("开始答案生成模块！！问题是:{}".format(self.context.get_question()))
                references = self.context.get_references_result()
                cot_dag = self.context.get_dag()
                assert isinstance(cot_dag, IGraph), ContextLogger(self.context).error("传入的graph 是一个IGraph类")
                single_hop = True
                if cot_dag.is_complex:
                    single_hop = False

                ContextLogger(self.context).info("\n 是否是一个思维链问题？{}".format(
                    "否" if single_hop else "是"
                ))
                doc_answer = MultiRoundRagAnswer(
                    question=self.context.get_question(), references=references,
                    multi_hop_qa_dag=cot_dag,
                    candidate_images=self.context.get_fig_result(application='QuestionAnswer'),
                    context=self.context
                )
                ContextLogger(self.context).info("\ncontext.get_answer: 图片池个数: {}".format(
                    len(self.context.get_fig_result(application='QuestionAnswer'))
                ))
                answer_generator = doc_answer.query_answer(single_hop=single_hop, question_level=0, streaming=streaming)

            # 流式输出部分
            final_answer_list = []
            current_answer = ""
            final_answer = ""
            for item in answer_generator:
                if isinstance(item, str):
                    if '<GraTAG type=\"image\" id=' not in item:
                        final_answer += item
                        current_answer += item
                    else:
                        final_answer_list.append({"text": current_answer})
                        final_answer_list.append({"text-image": item})
                        current_answer = ""
                    res = {
                        "type": "text",
                        "data": item,
                        "query": query,
                        "qa_series_id": qa_series_id,
                        "qa_pair_collection_id": qa_pair_collection_id,
                        "qa_pair_id": qa_pair_id
                    }
                    yield f"data: {json.dumps(res, ensure_ascii=False)}\0".encode(errors="ignore")
                elif isinstance(item, dict):
                    if item['type'] == 'image':
                        final_answer_list.append({"image": item})
                        ContextLogger(self.context).info(
                            "流式输出图片！！！{}".format({
                                "type": item['type'],
                                "data": item['data'],
                                "query": query,
                                "qa_series_id": qa_series_id,
                                "qa_pair_collection_id": qa_pair_collection_id,
                                "qa_pair_id": qa_pair_id
                            }))
                    else:
                        ContextLogger(self.context).info("\n item is: \n{}".format(item))
                    res = {
                        "type": item['type'],
                        "data": item['data'],
                        "query": query,
                        "qa_series_id": qa_series_id,
                        "qa_pair_collection_id": qa_pair_collection_id,
                        "qa_pair_id": qa_pair_id
                    }
                    yield f"data: {json.dumps(res, ensure_ascii=False)}\0".encode(errors="ignore")
            # 最终答案
            ContextLogger(self.context).info("\n In task get_answer， Answer is: \n{}\n\n{}".format(
                final_answer, self.final_answer_log_debug(final_answer)
            ))
            self.context.set_answer(final_answer)
            if doc_answer:
                assert isinstance(self.context.get_answer(), str) and len(
                    self.context.get_answer()) > 0, "答案的长度不满足要求！buffer_debug: {}".format(
                    doc_answer.buffer_debug)
            ContextLogger(self.context).info("流式输出结束！！！")

        except Exception as e:
            ContextLogger(self.context).error(traceback.print_exc())
            res = {
                "type": "error",
                "data": traceback.format_exc(),
                "query": query,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id,
            }
            yield f"data: {json.dumps(res, ensure_ascii=False)}\0".encode(errors="ignore")

    def get_query_answer_without_streaming(self, query, qa_series_id, qa_pair_collection_id, qa_pair_id):
        try:
            assert self.context.get_session_id() is not None, ContextLogger(self.context).error("请求session为空")
            assert self.context.get_request_id() is not None, ContextLogger(self.context).error("请求request_id为空")
            assert self.context.get_question_id() is not None, ContextLogger(self.context).error("请求question_id为空")
            assert self.context.get_question() is not None, ContextLogger(self.context).error("请求question为空")
            assert "use_for_check_items" in self.context.get_references_result() and len(
                self.context.get_references_result()["use_for_check_items"]) > 0, ContextLogger(self.context).error(
                "传入的reference为空")

            ContextLogger(self.context).info("开始答案生成模块！！问题是:{}".format(self.context.get_question()))
            references = self.context.get_references_result()
            cot_dag = self.context.get_dag()
            assert isinstance(cot_dag, IGraph), ContextLogger(self.context).error("传入的graph 是一个IGraph类")
            single_hop = True
            if cot_dag.is_complex:
                single_hop = False

            ContextLogger(self.context).info("\n 是否是一个思维链问题？{}".format(
                "否" if single_hop else "是"
            ))

            ContextLogger(self.context).info("\ncontext.get_answer: 图片池个数: {}".format(
                len(self.context.get_fig_result(application='QuestionAnswer'))
            ))
            doc_answer = MultiRoundRagAnswer(
                question=self.context.get_question(), references=references,
                multi_hop_qa_dag=cot_dag, candidate_images=self.context.get_fig_result(application='QuestionAnswer'),
                context=self.context
            )
            final_answer_dict = doc_answer.query_answer(single_hop=single_hop, question_level=0, streaming=False)
            # 最终答案
            ans = final_answer_dict['answer']
            # 引用挂载
            ContextLogger(self.context).info("\n In task get_answer， Answer is: \n{}\n\n{}".format(
                ans, self.final_answer_log_debug(ans)
            ))
            ref_dict = references['use_for_check_items']
            used_references, ans = add_references_to_doc(
                ref_dict, ans, doc_answer.QAConfig, is_continue_ref=False)
            self.context.set_answer(ans)
            final_answer_dict['final_ans_with_ref'] = ans
            final_answer_dict['all_references'] = ref_dict
            assert isinstance(self.context.get_answer(), str) and len(
                self.context.get_answer()) > 0, "答案的长度不满足要求！"
            return final_answer_dict
        except Exception as e:
            ContextLogger(self.context).error(traceback.print_exc())
            res = {
                "type": "error",
                "data": traceback.format_exc(),
                "query": query,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id,
            }
            return res

    def final_answer_log_debug(self, final_answer: str):
        """
        在log中最终答案展示部分加入引证的使用情况，方便debug
        """
        reference_indexes_in_answer = re.findall("\\[[a-zA-Z0-9]{8}]", final_answer)
        debug_log = "引证使用情况：\n"
        if isinstance(self.context, DocQAContext):
            reference_lib = self.context.ref_answer
            for each_index in reference_indexes_in_answer:
                for each_ref in reference_lib:
                    if each_ref["_id"] == each_index:
                        debug_log += "{}:{}\n".format(each_index, each_ref["content"])
                        break
        else:
            reference_lib = self.context.get_references_result()["use_for_check_items"]
            for each_index in reference_indexes_in_answer:
                try:
                    debug_log += "{}:{}\n".format(each_index, reference_lib[each_index]["description"])
                except KeyError:
                    pass
        return debug_log


if __name__ == '__main__':
    import time
    from include.utils.skywalking_utils import trace_new, start_sw
    from modules.recall_group.recall_group import RecallTask

    start_sw()

    test_question_list = [
        # "星环科技这家公司是做什么起家的",
        # "太阳是从哪边升起的？",
        "安徽怀远今天发生了哪些事？",
        "列举山西省农业农村厅制定的技术支撑文件中包含的主要内容。",
        "关于“姜萍”这一热点事件，大家的看法是什么？",
        "今天上海有什么新闻？其中哪些新闻是关于房地产的？",
        "世界各地如何谴责北约这一冷战余孽危害全球和平与安全的？",
        "黄河的水为什么变清了？解释背后的原因是什么？这说明了什么？",
        "世界各地如何谴责北约这一冷战余孽危害全球和平与安全的？",
        "请问，2024年上海市专精特新企业补贴范围是什么？",
        "列举山西省农业农村厅制定的技术支撑文件中包含的主要内容。",
        "世界各地如何谴责北约这一冷战余孽危害全球和平与安全的？",
    ]
    for i, query_i in enumerate(test_question_list[0:1]):
        session_idx = "mock_session_{}".format(i)
        context = RagQAContext(session_id=get_md5(session_idx))
        context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                    question_id=get_md5("{}_qe".format(session_idx)), question=query_i)
        context.set_basic_user_info({"User_Date": time.time(), "User_IP": '39.99.228.188'})
        context.set_retrieval_field({
            'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])
        })
        # context.set_QA_quickpass()
        # 模拟建思维链
        cot = QueryDivisionBasedCoTTask(context).get_cot(use_scene="general", if_parallel=True, split_num_threshold=6)
        dag = context.get_dag()

        # 模拟召回
        context.reset_reference()
        ref_page = None
        if RagQAConfig["WHITE_LIST_CONFIG"]["is_use"] == 'true':
            try:
                whitelist_response = search_whitelist(
                    scheme_id=RagQAConfig["WHITE_LIST_CONFIG"]["query_answer"]["scheme_id"],
                    input_info={"query": context.get_question()})
                if whitelist_response is not None:
                    cache_result = whitelist_response[0]['output']
                    stream_info, ref_answer, ref_page = (cache_result['stream_info'],
                                                         cache_result['ref_answer'],
                                                         cache_result['ref_page'],)

            except Exception as e:
                print("error during search_white_list")
        if not ref_page:
            response_graph = RecallTask(context).get_graph_recall(dag)

        # 生成答案
        answer_generator = QueryAnswerTask(context).get_query_answer(
            context.get_question(), "qa_series_id", "qa_pair_collection_id", "qa_pair_id")
        answer_list = []
        for answer in answer_generator:
            item_decoded = answer.decode().replace("data:", "").replace("\x00", "")
            item_json = json.loads(item_decoded)
            if item_json.get("type") == "text":
                print(item_json["data"], end="")
            elif isinstance(item_json, dict) and item_json['type'] == 'image':
                print("\n IMAGE: id: {}, url: {}".format(item_json['data'][-1]['id'], item_json['data'][-1]['url']))
            answer_list.append(item_json)
        ContextLogger(context).info("context.get_answer:{}".format(context.get_answer()))
