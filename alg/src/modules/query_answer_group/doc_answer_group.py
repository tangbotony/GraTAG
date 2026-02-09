import json
import copy
import traceback
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.context import DocQAContext
from include.logger import ContextLogger
from include.utils.text_utils import get_md5
from include.utils.Igraph_utils import IGraph
from include.utils.call_white_list import search_whitelist
from include.config import CommonConfig, DocQAConfig

from modules.query_answer_group.query_answer_group import QueryAnswerTask
from modules.query_division_based_cot_group import QueryDivisionDocCoTTask
from modules.query_answer_group.query_answer.multi_round_answer_agent_pdf import MultiRoundPDFDocAnswer
from modules.pdf_extraction_group.pdf_fig_table_finder import pdf_fig_table_find
from include.utils.chart_understanding import chart_understanding
from include.decorator import timer_decorator
import time
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']


class DocAnswerTask(QueryAnswerTask):
    """ 多轮文档回答
    input: XXXX
    output: XXXX
    """
    def __init__(self, doc_qa_context: DocQAContext):
        super().__init__(doc_qa_context)
        self.context = doc_qa_context
        self.clogger = ContextLogger(self.context)
        self.module_name = "DocAnswerTask"

    @timer_decorator
    def get_query_answer(self, query, qa_series_id, qa_pair_collection_id, qa_pair_id, streaming=True):
        try:
            assert self.context.get_session_id() is not None, ContextLogger(self.context).error("请求session为空")
            assert self.context.get_request_id() is not None, ContextLogger(self.context).error("请求request_id为空")
            assert self.context.get_question_id() is not None, ContextLogger(self.context).error("请求question_id为空")
            assert self.context.get_question() is not None, ContextLogger(self.context).error("请求question为空")
            ContextLogger(self.context).info("Question is: {}".format(self.context.get_question()))
            ContextLogger(self.context).info(
                "\n Pro flag in query answer: {}".format(self.context.get_single_question().get_pro_flag()))

            # 白名单查询
            answer_generator = None
            ref_answer = None
            doc_answer = None
            if self.QAConfig["WHITE_LIST_CONFIG"]["is_use"] == 'true':
                try:
                    search_query = self.context.get_origin_question() + str(self.context.get_doc_qa_pdf_names())
                    # search_query = "假设你是著名的首席宏观经济分析师，请你仔细阅读这篇宏观研究报告，并写一篇1000字左右的总结。['20240710_广发证券*宏观专题*郭磊 王丹*广发证券-广发宏观-锚定价格端：2024年中期产业链展望-郭磊-宏观经济研究-2024-07-10']"
                    whitelist_response = search_whitelist(
                        scheme_id=DocQAConfig["WHITE_LIST_CONFIG"]["doc_answer"]["scheme_id"],
                        input_info={"query": search_query})
                    if whitelist_response is not None:
                        cache_result = whitelist_response[-1]['output']
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
                ref_answer = self.context.get_ref_answer(pro_flag=self.context.get_single_question().get_pro_flag())
            res = {
                "type": "ref_answer",
                "data": ref_answer,
                "qa_series_id": qa_series_id,
                "qa_pair_collection_id": qa_pair_collection_id,
                "qa_pair_id": qa_pair_id
            }
            yield f"data: {json.dumps(res, ensure_ascii=False)}\0".encode(errors="ignore")

            if not answer_generator:

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
                doc_answer = MultiRoundPDFDocAnswer(
                    question=self.context.get_question(), references=references,
                    multi_hop_qa_dag=cot_dag, candidate_images=self.context.get_fig_result(application='DocAnswer'),
                    context=self.context
                )
                ContextLogger(self.context).info("\ncontext.get_answer: 图片池个数: {}".format(     # 打开
                    len(self.context.get_fig_result(application='DocAnswer'))
                ))
                answer_generator = doc_answer.query_answer(single_hop=single_hop, streaming=streaming)

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
            self.context.set_final_answer_list(final_answer_list)
            self.send(query=self.context.get_question(), answer_content=final_answer)
            if doc_answer:
                assert isinstance(self.context.get_answer(), str) and len(
                    self.context.get_answer()) > 0, "答案的长度不满足要求！buffer_debug: {}".format(doc_answer.buffer_debug)
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

    @timer_decorator
    def get_figure_table_answer(self, **kwargs):
        try:
            pro_flag = kwargs.get('pro_flag', True)
            # 获取图表信息
            st_time=time.time()
            figure_table_info=self.context.get_related_figtable()
            figure_table_dict={}
            for ft_item in figure_table_info:
                oss_id_item=ft_item.oss_id
                if oss_id_item not in figure_table_dict:
                    figure_table_dict[oss_id_item]=[]
                type=ft_item.type
                page_num=ft_item.page
                poly=ft_item.poly
                text=ft_item.text

                single_info = {
                    "type":type,
                    "page_num":page_num,
                    "poly":poly,
                    "text":text
                }
                figure_table_dict[oss_id_item].append(single_info)

            # 查询图表内容
            figure_table_content_list={}
            for oss_id_it,ft_info_it in figure_table_dict.items():
                search_list=[]
                for single_it in ft_info_it:
                    single_search_info=(single_it["type"],single_it["page_num"],single_it["poly"])
                    search_list.append(single_search_info)

                figure_table_content_item=pdf_fig_table_find(oss_id=oss_id_it, outline_elements=search_list)
                figure_table_content_list.update({oss_id_it:figure_table_content_item})

            # 整合图表内容和元信息
            for oss_id_it, ft_info_it in figure_table_dict.items():
                ft_content_it=figure_table_content_list.get(oss_id_it,"")
                for idx,single_ft_content_it in ft_content_it.items():
                    figure_table_dict[oss_id_it][idx].update({"ft_content":single_ft_content_it})

            # 独立图表信息
            figure_list=[]
            table_list=[]
            for oss_id_it, ft_info_it in figure_table_dict.items():
                for single_ft_info in ft_info_it:
                    ft_content=single_ft_info.get("ft_content",[])
                    if not ft_content:
                        continue
                    if single_ft_info["type"]=="figure_caption":
                        figure_list.append({"oss_id":oss_id_it,"ft_info":single_ft_info})
                    else:
                        table_list.append({"oss_id": oss_id_it, "ft_info": single_ft_info})
            # 图片问答
            image_ossid_list = []
            user_question = self.context.get_question()
            image_desc_list = []
            pdf_ossid_list = []
            figure_ft_info_list = []
            for figure_item in figure_list:
                for idx,ft_content_item in enumerate(figure_item["ft_info"]["ft_content"]):
                    image_ossid_item=os.path.join(DocQAConfig["CHART_UNDERSTANDING"]["path_prefix"],figure_item["ft_info"]["ft_content"][idx][2])
                    image_ossid_list.append(image_ossid_item)
                    image_desc_list.append(figure_item["ft_info"]["text"])
                    pdf_ossid_list.append(figure_item["oss_id"])
                    figure_ft_info_list.append(figure_item["ft_info"])
            query_list = [user_question] * len(image_ossid_list)
            if pro_flag:
                figure_answer = chart_understanding(image_ossid_list, query_list, image_desc_list,pdf_ossid_list,figure_ft_info_list)
            else:
                figure_answer = list()
            # 表格内容
            table_answer = []
            for table_item in table_list:
                for idx,ft_content_item in enumerate(table_item["ft_info"]["ft_content"]):
                    table_content=table_item["ft_info"]["ft_content"][idx][1]
                    table_caption=table_item["ft_info"]["text"]
                    if len(table_content)>0:
                        table_answer.append({"query":user_question,"ans":table_content,"caption":table_caption,"type":"table","oss_id":table_item["oss_id"],"ft_info":table_item["ft_info"]})
            ft_answer=figure_answer[:]
            ft_answer.extend(table_answer)
            # 图表内容存入context
            self.context.set_figure_table_answer(ft_answer)
            ed_time = time.time()
            cost_time = round(ed_time - st_time, 2)
            ContextLogger(self.context).warning(f"figure count:{len(image_ossid_list)},figure  cost time:{str(cost_time)}")
            return {
                "is_success": True,
                "return_code": "",
                "detail": "",
                "timestamp": "",
                "err_msg": ""
            }

        except Exception as e:
            ContextLogger(self.context).warning(traceback.print_exc())

    def send(self, query, answer_content):
        bot = self.bot
        bot.send_card(self.context.get_user_id(), self.module_name,
                      "- **Query：{}**\n "
                      "- **Module name：{}**\n "
                      "- **Session id：{}**\n "
                      "- **Request id：{}**\n "
                      "- **User id：{}**\n "
                      "- **QA_answer：{}**\n ".format(query,
                      self.module_name,
                      self.context.get_session_id(),
                      self.context.get_single_question().get_request_id(),
                      self.context.get_user_id(), answer_content)
        )


if __name__ == '__main__':
    import time
    from include.utils.skywalking_utils import start_sw
    start_sw()

    from modules.recall_group.recall_group import RecallTask
    test_question_list = [
        "安徽怀远今天发生了哪些事？"
    ]
    for i, query_i in enumerate(test_question_list[0:1]):
        session_idx = "mock_session_{}".format(i)
        context = DocQAContext(session_id=get_md5(session_idx))
        context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                    question_id=get_md5("{}_qe".format(session_idx)), question=query_i)
        context.set_basic_user_info({"User_Date": time.time(), "User_IP": '39.99.228.188'})
        context.set_retrieval_field({
            'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])
        })
        # context.set_QA_quickpass()
        # 模拟建思维链
        cot = QueryDivisionDocCoTTask(context).get_cot(use_scene="general", if_parallel=True, split_num_threshold=6)
        dag = context.get_dag()

        # 模拟召回
        context.reset_reference()
        ref_page = None
        if DocQAConfig["WHITE_LIST_CONFIG"]["is_use"] == 'true':
            try:
                whitelist_response = search_whitelist(
                    scheme_id=DocQAConfig["WHITE_LIST_CONFIG"]["doc_answer"]["scheme_id"],
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
        answer_generator = DocAnswerTask(context).get_query_answer(
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

