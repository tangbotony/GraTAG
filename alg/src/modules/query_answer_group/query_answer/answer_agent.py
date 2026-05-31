# coding:utf-8
# Answer Generation
import re
import copy
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor

import requests
import traceback
import datetime
import threading
import queue
import concurrent.futures
from include.logger import log
from include.logger import ContextLogger
from include.config import PromptConfig, RagQAConfig, CommonConfig, DocQAConfig
from include.rag.search.query_all import is_valid_url
from include.utils.llm_caller_utils import llm_call
from include.utils.text_utils import get_other_content, get_otherQA_content, get_length_bin, validate_and_filter_codes
from include.context import RagQAContext, DocQAContext
from include.utils.es_utils import load_from_es, save_to_es
from include.rag.rag_recall_agent import RagRecall
from include.query_intent_recognition import get_reinforced_qkw
from modules.query_division_based_cot_group import QueryDivisionBasedCoTTask
from include.rag.choose_top_ref import get_reference, get_reference_balanced
from include.utils.Igraph_utils import IGraph
from include.utils.call_fig_func import get_fig, get_fig_filter
from include.utils.add_ref_to_doc import add_references_to_doc
from include.utils.multi_hop_qa_utils import set_multi_hop_sub_queries, get_multi_hop_sub_queries, get_chain_queries, get_chain_queries_qa
from include.decorator import timer_decorator
from include.utils.similarity_utils import get_similarity


def get_chinese_date():
    # 获取今天的日期
    today = datetime.date.today()

    # 将日期格式化为中文格式：年-月-日
    chinese_format_date = today.strftime('%Y年%m月%d日')

    return chinese_format_date


def get_candidate_lib(candidate_images: list, session_id: str, request_id: str, question: str, add_fig: str = 'true', pro_flag=True):
    candidate_images_set = set()
    candidate_images_info = dict()
    for fig in candidate_images:
        if fig.get('url', '') != '':
            candidate_images_set.add(fig['url'])

    candidate_images_dict_for_filter = dict()
    for fig in candidate_images:
        if fig.get('url', '') != '':
            candidate_images_dict_for_filter[fig.get('url', '')] = {
                "origin_doc_url": fig.get('origin_doc_url', ''),
                "above_content": fig.get('above_content', ''),
                "below_content": fig.get('below_content', ''),
                "title": fig.get('title', ''),
                "search_word": fig.get('search_word', ''),
                "origin_img_url": fig.get('origin_img_url', ''),
            }
            if fig.get('height', None) and fig.get('width', None):
                candidate_images_dict_for_filter[fig.get('url', '')].update(
                    {
                        "height": fig.get('height'),
                        "width": fig.get('width')
                    }
                )
    filtered_candidate_images_set = set()
    if add_fig == 'true' and pro_flag:
        filtered_candidate_images_set, _ = get_fig_filter({
                            "session_id": session_id,
                            "request_id": request_id,
                            "question": question,
                            "candidate_images": list(candidate_images_set),
                            "candidate_images_dict": candidate_images_dict_for_filter
        }, application='qa')

        


        for fig in candidate_images:
            if fig.get('url', '') != '' and fig.get('url', '') in filtered_candidate_images_set:
                candidate_images_info[fig.get('url', '')] = {
                    "origin_doc_url": fig.get('origin_doc_url', ''),
                    "above_content": fig.get('above_content', ''),
                    "below_content": fig.get('below_content', ''),
                    "title": fig.get('title', ''),
                    "search_word": fig.get('search_word', ''),
                    "origin_img_url": fig.get('origin_img_url', ''),
                }
                if fig.get('height', None) and fig.get('width', None):
                    candidate_images_info[fig.get('url', '')].update(
                        {
                            "height": fig.get('height'),
                            "width": fig.get('width')
                        }
                    )
    return set(filtered_candidate_images_set), candidate_images_info


def get_response_with_ref(response_i, use_for_check_items):
    # 对修正的结果以及参考文献的位置进行处理，满足接口需求
    used_ref_items = dict()
    for key in use_for_check_items.keys():
        if key in response_i:
            used_ref_items[key] = use_for_check_items[key]
    return used_ref_items


def extract_references(text):
    # Split the text into sentences
    sentences_re = re.split(r'(?<=[。？！\n…!?])', text)
    sentences = []
    for sentence in sentences_re:
        if sentence != "":
            sentences.append(sentence)
    # Create a dictionary to store references and their associated texts
    ref_dict = {}

    # Iterate over each sentence and find references
    for sentence in sentences:
        refs = re.findall(r'\[\w+\]', sentence)
        for ref in refs:
            # Remove the reference from the sentence to get the associated text
            associated_text = re.sub(r'\[\w+\]', '', sentence).strip()
            # Add the associated text to the reference in the dictionary
            if ref in ref_dict:
                if associated_text not in ref_dict[ref]:
                    ref_dict[ref].append(associated_text)
            else:
                ref_dict[ref] = [associated_text]

    return ref_dict


def stream_query_answer(query: str, model_name: str, temperature: float = 0.7, top_p: float = 0.8,
                        max_tokens: int = 8000,
                        frequency_penalty: float = 0.1, config=CommonConfig, clogger=log, add_template=True,
                        **kwargs):
    assert model_name in list(config["MODEL_CONFIG"].keys()), "调用模型未配置"
    assert "index" in config["MODEL_CONFIG"][model_name], "未配置调用模型index"
    assert "prompt_template" in config["MODEL_CONFIG"][model_name], "未配置调用模型prompt_template"

    # if "task_name" in kwargs:
    #     clogger.info("\n 正在【{}】任务中调用模型【{}】".format(kwargs["task_name"], model_name))
    # else:
    #     clogger.info("\n 正在调用模型【{}】".format(model_name))
    if add_template:
        query = config["MODEL_CONFIG"][model_name]["prompt_template"].format(query)
    payload = json.dumps({
        "model": config["MODEL_CONFIG"][model_name]["index"],
        "params": {
            "request_id": "",
            "prompt": query,
            "temperature": temperature,
            "top_p": top_p,
            "n": 1,
            "max_tokens": max_tokens,
            "frequency_penalty": frequency_penalty
        }
    })
    headers = {'token': config["AUTH_CONFIG"]["key"],
               'Content-Type': 'application/json',
               'Accept': '*/*',
               'Connection': 'keep-alive'
               }
    url = config["MODEL_CONFIG"]["stream_url"]
    response = requests.request("POST", url, headers=headers, data=payload, stream=True)

    def stream_generator():
        # clogger.info("start getting stream output of {}".format(query))
        curr_str = ''
        filter_done = False
        filter_str = "[回答]:"
        try:
            for chunk in response.iter_lines(chunk_size=1024, decode_unicode=False,
                                             delimiter=b"\0"):  # Adjust chunk_size as needed
                if chunk:
                    # Do something with each chunk of data
                    data = chunk.decode('utf-8')
                    if data.startswith("data: ") and data != "data: [DONE]\n\n":
                        data = data[len("data: "):]
                        data = json.loads(data.strip())
                        curr_str += data['text']
                        if not filter_done:
                            if filter_str in curr_str:
                                filter_done = True
                                curr_str = curr_str.split(filter_str)[-1]
                                if len(curr_str) != 0:
                                    if curr_str[0] == "\n":
                                        curr_str = curr_str[1:]
                                    yield curr_str
                            else:
                                if len(curr_str) >= 14:
                                    filter_done = True
                                    yield curr_str
                        else:
                            yield data['text']
        except Exception as e:
            traceback.print_exc()
            log.warning("stream_generator occur error: {}".format(e.__str__()))
            yield "非常抱歉，暂时无法回答您的问题，请重试或询问其他问题"

    return stream_generator()


class DocAnswer:
    def __init__(
            self,
            question: str,
            references: dict,
            multi_hop_qa_dag: IGraph = None,
            max_try: int = 5,
            candidate_images: list = None,
            context: RagQAContext=None
    ):
        self.name = "DocAnswer"
        self.context = context
        self.QAConfig = RagQAConfig
        if type(self.context) is RagQAContext:
            self.QAConfig = RagQAConfig
        elif type(self.context) is DocQAContext:
            self.QAConfig = DocQAConfig

        # 记录问题和答案
        self._question = question
        self._references = references
        self._multi_hop_qa_dag = multi_hop_qa_dag
        self._answer = ""
        self._max_try = max_try
        self._answer_length = random.choice(range(200, 500, 50))
        self._max_input_tokens = 14000  # random.choice(range(14000, 15000, 50))  # 模型输入的最大长度
        self._paragraph_context = list()
        self._candidate_lib = None
        self._candidate_info = None
        executor = ThreadPoolExecutor()
        self._candidate_future = executor.submit(
            get_candidate_lib,
            candidate_images,
            context.get_session_id(),
            context.get_request_id(),
            context.get_question(),
            self.QAConfig['EXP_CONFIG']['add_fig'],
            context.get_single_question().get_pro_flag()
        )
        # self._candidate_lib, self._candidate_info = get_candidate_lib(
        #     candidate_images, context.get_session_id(), context.get_request_id(), context.get_question())
        self.fig_id = 0
        self._top_n_indices = 64

        # pattern match
        self.pattern_answer = r"\[回答\]:*(.*?)(#+)?$"
        self.pattern = "[回答]:"

        # 初始化知识库
        self.knowledge_database = []
        self._source_dict = {
            "net_kwargs": {
                "source": "1",
                "name": "百度检索"
            },  # 百度检索库
            "doc_kwargs": {
                "source": "1",
                "name": "舆情爬虫新闻es检索库"
            },  # 爬虫新闻 es检索库
            "credible_kwargs": {
                "source": "1",
                "name": "730个可信网站数据库"
            },  # 可信数据库
            "vector_data_base": {
                "source": "2",
                "name": "用户上传数据库"
            },  # 用户上传数据库
            "summary_kwargs": {
                "source": "3",
                "name": "新华社重要稿件库"
            },  # 新华社重要稿件库
            "xinhua_kwargs": {
                "source": "4",
                "name": "新华社内部数据库"
            }  # 新华社内部数据库
        }
        self.image_queue = queue.Queue()
        self.image_result_queue = queue.Queue()

    def get_candidate_info(self):
        if self._candidate_lib is None or self._candidate_info is None:
            self._candidate_lib, self._candidate_info = self._candidate_future.result()  # 这里会阻塞直到线程完成

    def query_answer(self, single_hop=True, streaming=False):
        if single_hop or not self._multi_hop_qa_dag:
            return self._call_single_hop_answer(streaming=streaming)
        else:
            return self._call_multi_hop_answer(streaming=streaming)

    def _get_sub_query(self, sub_query, origin_query_2_ref_query, ref_multi_hop_list, add_title=False):
        sub_ref_query = origin_query_2_ref_query[sub_query]
        if sub_ref_query in ref_multi_hop_list:
            _, _, ref_str_sub_query_i = ref_multi_hop_list[sub_ref_query]
        else:
            ref_str_sub_query_i = []
        upstream_queries = get_chain_queries(self._multi_hop_qa_dag, sub_query)
        upstream_qa, qa_chain_reference = get_chain_queries_qa(self._multi_hop_qa_dag, upstream_queries,
                                                               self.QAConfig['EXP_CONFIG']['is_fast'])
        ref_str_sub_query_i = copy.deepcopy(qa_chain_reference + ref_str_sub_query_i)
        ans_sub_query_i = self._single_answer(
            sub_query, ref_str_sub_query_i, message="", mode='query_simple_answer', streaming=False, add_title=add_title)
        return ans_sub_query_i

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
        chain_results['chain'] = query_turn
        ContextLogger(self.context).info("\n 思维链结果：{}".format(
            query_turn
        ))

        query_pairs = self._multi_hop_qa_dag.print_relation()
        multi_hop_qa_end_queries = []
        for query_pair_i in query_pairs:
            if query_pair_i[1] == 'End' and query_pair_i[0] not in multi_hop_qa_end_queries:
                multi_hop_qa_end_queries.append(query_pair_i[0])

        # 将所有检索到的资料拆分到子问题中。
        # 因为[新华社项目]不支持在回答子问题阶段召回参考材料，所以在[新华社项目]中，所有的子问题都必需挂载上证据。
        # 在[DEMO项目]中，能够在子问题引证问答的阶段继续召回证据。
        # TODO：综合上述原因，之后要在这里加两个参数：
        #   1. 是否支持在思维链问答中串行召回
        #   2. 在打散证据的时候，是否所有的子问题都要挂载证据/还是根据思维链图中的指示进行挂载
        ref_multi_hop_list = get_reference_balanced(
            use_for_check_items_internet_all, use_for_check_items_opinion_similarity_dic_internet_all,
            use_for_check_items_content_dic_internet_all, ref_query
        )

        chain_results['sub_query'] = []
        for query_turn_parallel_list in query_turn:
            def process_source(sub_query):
                sub_query_answer = self._get_sub_query(
                    sub_query, origin_query_2_ref_query, ref_multi_hop_list)
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

        all_qa, all_qa_chain_reference = get_chain_queries_qa(self._multi_hop_qa_dag, multi_hop_qa_end_queries,
                                                              self.QAConfig['EXP_CONFIG']['is_fast'])
        ref_str_sub_query_i = copy.deepcopy(all_qa_chain_reference)

        # 最终问题解答
        if streaming:
            return self._single_answer(
                self._question, ref_str_sub_query_i, message, mode='query_answer', streaming=streaming)
        else:
            final_answer = self._single_answer(
                self._question, ref_str_sub_query_i, message, mode='query_answer', streaming=streaming)
            chain_results['final_answer'] = copy.deepcopy(final_answer)
            final_answer['chain_results'] = chain_results
            return final_answer

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
                                   mode='query_simple_answer', streaming=streaming)

    @timer_decorator
    def _single_answer(self, question, ref_str_item_info_internet, message, mode='query_answer', streaming=False, add_title=False):
        use_for_check_items = dict()
        for ref in ref_str_item_info_internet:
            source = self._source_dict.get(ref["source"], dict()).get("source", '')
            source_name = self._source_dict.get(ref["source"], dict()).get("name", '')
            use_for_check_items[ref["key"]] = {
                "id": ref.get("id"), "description": ref.get("description"), "title": ref.get("title"),
                "url": ref.get("url"), "source": source, "source_id": ref.get("source_id"),
                "other_info": ref.get("other_info", dict()),
                "source_name": source_name
            }
        if streaming:
            return self._streaming_output_find_final_answer(
                ref_str_item_info_internet, question, use_for_check_items, mode=mode, add_title=add_title)
        else:
            # 如果挂载了检索材料/或是EXP_CONFIG中设置了无论是否挂载检索材料、都要回答的情况
            if self.QAConfig['EXP_CONFIG']['is_answer_when_absent_ref'] == 'true' or len(ref_str_item_info_internet) > 0:
                results, background_items, num_valid_results = self._find_final_answer(
                    ref_str_item_info_internet, question, use_for_check_items, mode=mode, add_title=add_title)
            else:
                ContextLogger(self.context).info(
                    "\n 该子问题[{}]没有挂载任何的reference：{}".format(question, ref_str_item_info_internet))
                results = None
            if results:
                for result in results:
                    if result["valid"]:
                        return result
                return results[0]
            else:
                message += "No valid answer because of no valid output from large language model."
                return {
                    "source": self.name,
                    "answer": "",
                    "input_llm": "",
                    "output_llm": "",
                    "reference": "",
                    "valid": False,
                    "message": message
                }

    def _decode_answer_from_llm_raw_output(self, llm_raw_result: str):
        """
        解析大模型输出的答案、思路以及其他可能的材料，不同的prompt输出格式不同、解析的内容也不同
        """
        answer, thought = None, None
        answer = re.search(self.pattern_answer, llm_raw_result, re.DOTALL)
        return answer, thought

    def _decode_no_markdown_answer_from_llm_raw_output(self, llm_raw_result: str):
        """
        解析大模型输出的答案、思路以及其他可能的材料，不同的prompt输出格式不同、解析的内容也不同
        """
        answer, thought = self._decode_answer_from_llm_raw_output(llm_raw_result)
        if answer:
            res = answer.group(1)
            # 定义需要被过滤掉的模式
            pattern = r'\[[a-zA-Z0-9]+\]'
            # 使用正则表达式进行替换
            res = re.sub(pattern, '', res)
            return res
        else:
            return llm_raw_result

    def _find_final_answer(self, all_ref_items, question, use_for_check_items, mode='query_answer', add_title=False):
        ref_sentence = []
        raw_description = []
        for item_i, item in enumerate(all_ref_items):
            ref_publish_time = ""
            if is_valid_url(item["url"]):
                try:
                    raw_publish_time = datetime.datetime.strptime(item["other_info"]["publish_time"], "%Y-%m-%d %H:%M:%S")
                    ref_publish_time = "（发布于{}年{}月{}日）".format(raw_publish_time.year, raw_publish_time.month,
                                                                     raw_publish_time.day)
                except:
                    ref_publish_time = ""

            description = item["title"] + ref_publish_time + '：' + item["description"].replace("\r", " ").replace("\u3000", " ").replace(
                "\n",
                " ").strip() if (add_title and item['title'] != '') else item["description"].replace("\r", " ").replace("\u3000", " ").replace(
                "\n",
                " ").strip()
            ref_sentence.append('资料{}'.format(item_i) + ":" + description)
            raw_description.append(item['description'])

        results, input_final, results_raw = self._call_query_answer(
            question, ref_sentence, mode=mode, raw_description=raw_description, all_ref_items=all_ref_items
        )

        all_results = []
        new_background_items = []
        num_valid_results = 0
        for result in results:
            used_ref_item = get_response_with_ref(result, use_for_check_items)
            if len(result) > 0:
                final_answer = result.replace("\n\n", "\n")
                # 来自background的内容是否占总引用比例小于阈值，答案有效
                num_valid_results += 1
                all_results.append(
                    ({
                        "source": self.name,
                        "answer": final_answer,
                        "input_llm": input_final,
                        "output_llm": results_raw,
                        "reference": used_ref_item,
                        "valid": True,
                        "message": "Success!"
                      })
                )
        if num_valid_results > 0:
            return all_results, None, num_valid_results
        else:
            return all_results, new_background_items, num_valid_results

    def _streaming_output_find_final_answer(self, all_ref_items, question, use_for_check_items, mode='query_answer', add_title=False):
        ref_sentence = []
        raw_description = []
        for item_i, item in enumerate(all_ref_items):
            # ref_publish_time = ""
            # # if is_valid_url(item["url"]):
            try:
                raw_publish_time = datetime.datetime.strptime(item["other_info"]["publish_time"], "%Y-%m-%d %H:%M:%S")
                ref_publish_time = "（发布于{}年{}月{}日）".format(raw_publish_time.year, raw_publish_time.month,
                                                                 raw_publish_time.day)
            except:
                ref_publish_time = ""
            description = item["title"] + ref_publish_time + '：' + item["description"].replace("\r", " ").replace("\u3000", " ").replace(
                "\n",
                " ").strip() if (add_title and item['title'].strip() != '' and (item['title'].strip() != item['description'].strip())) else item["description"].replace("\r", " ").replace("\u3000", " ").replace(
                "\n",
                " ").strip()
            # ref_sentence.append("资料{}".format(item_i) + ":" + description)
            id = item["id"]
            if type(self.context) is DocQAContext:
                # 文档问答中材料格式
                # ref_sentence.append(f"{id}:{description}")
                ref_sentence.append("资料{}".format(item_i) + ":" + description)
            else:
                # qa问答中材料格式
                ref_sentence.append(f"\t- {id}:{description}")
            raw_description.append(item['description'])
        ref_dict = self._references['use_for_check_items']

        ref_docs = set()
        for ref_i in ref_dict.values():
            ref_docs.add(ref_i['other_info']['doc_id'])
        ContextLogger(self.context).info("\n 准备开始流式输出！！！！ 待挂载的引证chunk个数：{}, 待挂载的引证doc个数：{}".format(
            len(ref_dict.keys()), len(ref_docs)
        ))
        return self._streaming_output_query_answer(
            question, ref_sentence, n=1, mode=mode, raw_description=raw_description, all_ref_items=all_ref_items)

    def _get_prompt(self, question, ref_content, **kwargs):
        mode = kwargs.get('mode', "query_answer")
        def iterative_add_prompt(prompt_template):
            datestr = get_chinese_date()
            prompt_dic = {
                "query":question,
                "ref_content":"",
                "date":datestr,
                "date_2":datestr
            }
            if mode in ["query_answer", "query_answer_quickpass"]:
                prompt_dic.update({"related_QA":""})
            # step1 初步加载
            prompt_init = prompt_template.format(**prompt_dic)

            # step2 搜索字数限制，筛选子问题问答信息
            if mode in ["query_answer", "query_answer_quickpass"]:
                related_QA = get_otherQA_content(
                    prompt_init, self._multi_hop_qa_dag, self._max_input_tokens, mode,
                    is_answer_when_absent_ref=self.QAConfig['EXP_CONFIG']['is_answer_when_absent_ref'])
                prompt_dic.update({"related_QA":related_QA})
                # 再次初步加载
                prompt_init = prompt_template.format(**prompt_dic)

            # step3 搜索字数限制，筛选参考文献来源
            ref_content_short = get_other_content(prompt_init, ref_content, self._max_input_tokens)
            prompt_dic.update({"ref_content":ref_content_short})

            iterative_added_prompt = prompt_template.format(**prompt_dic)
            return iterative_added_prompt

        # 载入预定义的PROMPT模版
        if self.context.get_single_question().get_pro_flag():
            instruction_temp = PromptConfig[mode]['instruction']
        else:
            instruction_temp = PromptConfig[mode + '_non_pro']['instruction']
        if mode in ["query_simple_answer", "query_answer", "query_answer_quickpass"]:
            prompt_final = iterative_add_prompt(instruction_temp)
        else:
            raise NotImplementedError
        prompt_final = prompt_final.replace('None', '无').replace('NONE', '无').replace('none', '无')
        return prompt_final
        
    def _get_model_name(self, mode, tmp_question):
        if type(self.context) is RagQAContext:
            if not self.context.get_single_question().get_pro_flag():
                return RagQAConfig['TASK_MODEL_CONFIG']['generate_answer_pro_flag']
            elif tmp_question == self._question:
                return RagQAConfig['TASK_MODEL_CONFIG']['generate_answer']
        elif type(self.context) is DocQAContext:
            return self.QAConfig['TASK_MODEL_CONFIG']['generate_answer']
        # if mode in ['query_answer', 'query_answer_quickpass']:
        #     model_name = self.QAConfig['TASK_MODEL_CONFIG']['generate_answer']
        # elif mode in ['query_simple_answer']:
        #     model_name = self.QAConfig['TASK_MODEL_CONFIG']['generate_sub_answer']
        # return model_name

    def _add_ref_to_doc_line(self, answer):
        # 挂载reference, 并check格式
        answer = validate_and_filter_codes(answer)
        # 不对大小标题、带冒号的短句进行引证挂载
        if ("#" in answer or ("*" in answer and len(answer) < 10) or (':' in answer and len(answer) < 10) or
                ("：" in answer and len(answer) < 10)):
            return answer
        ref_dict = self._references['use_for_check_items']
        final_ref_lib, final_answer = add_references_to_doc(ref_dict, answer, self.QAConfig, is_continue_ref=False, session_id=self.context.get_session_id())
        for final_ref_i in final_ref_lib.values():
            if isinstance(final_ref_i.get('other_info', dict()).get('images', list()), list):
                for image in final_ref_i['other_info']['images']:
                    if image['url'] and image['url'] in self._candidate_lib:
                        self.ref_code_list.add(image['url'])
        return final_answer

    def _streaming_output_query_answer(self, question: str, ref_content, n=1, mode='query_answer', fig=True, **kwargs):
        model_name = self._get_model_name(mode, question)
        prompt_final = self._get_prompt(question, ref_content, mode = mode, **kwargs)
        self.context.set_llm_final_input(prompt_final)
        ContextLogger(self.context).info(f"最终问题回答 prompt:{prompt_final}, model: {model_name}")
        llm_output_generator = llm_call(
            query=prompt_final,
            model_name=model_name,
            is_stream=True,
            temperature=0.0,
            session_id=self.context.get_session_id()
        )
        self.context.add_sft_info({
            "mode": mode,
            "llm_input": prompt_final
        })
        return self._filter_generator(llm_output_generator)

    def fig_func(self, input_param_dict):
        paragraph_context = input_param_dict['paragraph_context']
        min_context_len = input_param_dict['min_context_len']
        delimiter_in_buffer = input_param_dict['delimiter_in_buffer']
        output_line = input_param_dict['output_line']
        self.text_length_since_last_time += len(output_line)
        must_fig = input_param_dict.get('must', False)
        if (((self.text_length_since_last_time > min_context_len and delimiter_in_buffer == '\n') or must_fig) and
                RagQAConfig['EXP_CONFIG']['add_fig'] == "true" and len(list(self._candidate_lib)) > 0 and
                self.context.get_single_question().get_pro_flag()):
            # 不对大小标题、带冒号的短句进行引证挂载
            last_text = paragraph_context[-1]['content'].strip().split('\n')
            last_text = last_text[-1]
            if not ("#" in last_text or ("*" in last_text and len(last_text) < 10) or (':' in last_text and len(last_text) < 10) or
                    ("：" in last_text and len(last_text) < 10)) or must_fig:
                if self.QAConfig['FIG_CONFIG']["is_limit_candidate_image"] == "true":
                    input_ref_code = set()
                    for ref in self.ref_code_list:
                        if ref in self._candidate_lib:
                            input_ref_code.add(ref)
                    if len(input_ref_code) <= self.QAConfig['FIG_CONFIG']["limit_candidate_image_size"]:
                        for ref_other in self._candidate_lib:
                            if ref_other not in input_ref_code and len(input_ref_code) <= self.QAConfig['FIG_CONFIG']["limit_candidate_image_size"]:
                                input_ref_code.add(ref_other)
                else:
                    input_ref_code = self._candidate_lib
                total_above_content = ''
                input_paragraph_context = list()
                for paragraph_i in paragraph_context:
                    if paragraph_i['type'] == 'text':
                        if paragraph_i['fig_pos_id'] > self.fig_pos_id_since_last_time:
                            input_paragraph_context.append(copy.deepcopy(paragraph_i))
                        elif paragraph_i['fig_pos_id'] <= self.fig_pos_id_since_last_time:
                            total_above_content += paragraph_i['content']

                res, is_fig = get_fig({
                    "session_id": self.context.get_session_id(),
                    "request_id": self.context.get_request_id(),
                    "question": self.context.get_question(),
                    "contexts": input_paragraph_context,
                    "candidate_images": list(input_ref_code),
                    "candidate_images_dict": self._candidate_info,
                    "total_above_content": total_above_content
                })
                res_copy = copy.deepcopy({
                    "session_id": self.context.get_session_id(),
                    "request_id": self.context.get_request_id(),
                    "question": self.context.get_question(),
                    "contexts": input_paragraph_context,
                    "candidate_images": list(input_ref_code),
                    "candidate_images_dict": self._candidate_info,
                    "total_above_content": total_above_content
                })
                if is_fig:
                    fig_id = None
                    url = None
                    # TODO: 当前仅支持在单次插图请求插入一张图片（接口访问多次可以实现插入N张图片）
                    for res_i in res:
                        if res_i['type'] == 'image':
                            url = res_i['url']
                            break
                        elif res_i['type'] == 'text':
                            fig_id = res_i['fig_pos_id']
                    if fig_id and url:
                        ContextLogger(self.context).info("\n 在fig{}中找到了合适的图片！！{}\n".format(fig_id, url))
                        self.data_list.append({
                            "id": '{}'.format(fig_id),
                            "url": url,
                            "origin_doc_url": self._candidate_info[url]["origin_doc_url"]
                        })
                        self._candidate_lib.discard(url)
                        self.text_length_since_last_time = 0
                        self.fig_pos_id_since_last_time = fig_id
                        return {
                                "type": "image",
                                "data": copy.deepcopy(self.data_list),
                        }
            else:
                log.debug("text: \nfull: {}, last_sentence: {}".format(
                    paragraph_context[-1]['content'].strip().split('\n'), last_text))
        return "no-image"

    def async_fig_func(self):
        while True:
            input_param_dict = self.image_queue.get()
            if input_param_dict is None:
                self.image_result_queue.put(None)
                self.image_queue.task_done()
                break
            result = self.fig_func(input_param_dict)
            self.image_result_queue.put(result)
            self.image_queue.task_done()

    # 首句处理（如果和用户输入的问题重复，则不展示）
    def first_sentence_modification(self, finish_start, output_line_old, user_question, delimiter_in_buffer):
        # 如果开没有检测到首句话，则进行首句话相似度判断
        if not finish_start:
            if len(output_line_old) >= 5:
                # 计算output_line和question的相似度
                similarity_with_question = get_similarity(
                    [output_line_old], [user_question])
                if similarity_with_question[0][0] > self.QAConfig['FIRST_SENTENCE_CONFIG']:
                    log.debug("\n 首句和问题重复！首句：{}, 问题：{}".format(output_line_old, user_question))
                    self.first_sentence_repeated = output_line_old
                    output_line_old = ''
                finish_start = True
        output_line = self._add_ref_to_doc_line(output_line_old)
        output_line = output_line.strip() + delimiter_in_buffer if output_line.strip() != '' else ''

        new_output_line_old = output_line_old + delimiter_in_buffer if output_line_old != '' else ''
        self._add_paragraph_to_context(new_output_line_old)
        return finish_start, output_line, new_output_line_old

    def _filter_generator(self, original_generator, delimiter=['\n', '。'], min_context_len=400):
        """
        A generator that accumulates characters from the original generator
        until it forms a segment based on the delimiter. Only segments longer
        than the specified minimum length are yielded.

        :param original_generator: The original generator to filter.
        :param min_length: The minimum length of the segment to yield.
        :param delimiter: The delimiter to split the input into segments.
        :if fig:
        test_input = {
            "contexts": [
                {
                    "type": "text",
                    "content": "毫无疑问，不久前俄罗斯总统普京访华，从中方这里得到了俄方想要的东西，双方达成的合作和共识，在中俄发表的联合声明中已经写得很清楚。回国后，普京还意犹未尽地致电中方最高层，感谢中方对他的盛情接待，声称此次访华之行，给其留下了真正美好而难忘的印象，评价双方的会谈进一步加强了两国的全面战略协作伙伴关系，他向中方承诺将继续加强密切合作，并指出，在俄罗斯的土地上，中方最高层永远是受欢迎的贵宾。"
                },...
            ],
            "candidate_images": [
                "https://XXXXXX/XX.jpeg",...
            ]
        }
        :return: A generator that yields only segments longer than min_length.
        """
        buffer = ""
        total_buffer = ""
        self.data_list = []
        self.text_length_since_last_time = 0
        self.fig_pos_id_since_last_time = 0
        finish_start = False

        # 小图片池，优先考虑在挂载的图片内的图片。
        self.ref_code_list = set()
        self.buffer_debug = ""

        # 启动异步任务处理线程
        self.get_candidate_info()  # 等待异步图像过滤进程结束 保证图像过滤结束
        ContextLogger(self.context).info("\n 准备开始流式输出！ 图片池：{}\n".format(self._candidate_lib))
        worker_thread = threading.Thread(target=self.async_fig_func)
        worker_thread.start()

        complete_organize_state = {
            "type": "state",
            "data": "complete"
        }
        yield complete_organize_state

        delimiter_in_buffer = '\n'
        all_yielded_buffer = ''
        self.first_sentence_repeated = ''
        for char in original_generator:
            # 对于首句，需要查看整段内容和原问题的相似度，如果相似度太高，就不显示。
            buffer += char
            total_buffer += char
            self.buffer_debug = total_buffer
            if any(delimiter_i in buffer for delimiter_i in delimiter):
                delimiter_in_buffer = [delimiter_i for delimiter_i in delimiter if delimiter_i in buffer][0]
                segment, buffer = buffer.split(delimiter_in_buffer, 1)
                if self.pattern in segment.strip():
                    answer_re, thought_re = self._decode_answer_from_llm_raw_output(segment)
                    if answer_re:
                        res = answer_re.group(1)
                        output_line_old = res
                        finish_start, output_line, new_output_line_old = self.first_sentence_modification(
                            finish_start, output_line_old, self.context.get_question(), delimiter_in_buffer)

                        for c in output_line.strip():
                            all_yielded_buffer += c
                            yield c
                        if delimiter_in_buffer == '\n':
                            yield '<GraTAG type="image" id="{}"/>'.format(self.fig_id)
                            yield '\n'
                            # 将任务放入任务队列
                            self.image_queue.put({
                                'paragraph_context': copy.deepcopy(self._paragraph_context),
                                'min_context_len': min_context_len,
                                'delimiter_in_buffer': delimiter_in_buffer,
                                'fig_id': self.fig_id,
                                'output_line': new_output_line_old,
                            })
                            self.fig_id += 1
                elif "######" not in segment.strip():
                    output_line_old = segment
                    finish_start, output_line, new_output_line_old = self.first_sentence_modification(
                        finish_start, output_line_old, self.context.get_question(), delimiter_in_buffer)
                    for c in output_line.strip():
                        all_yielded_buffer += c
                        yield c

                    if delimiter_in_buffer == '\n':
                        yield '<GraTAG type="image" id="{}"/>'.format(self.fig_id)
                        yield '\n'
                        # 将任务放入任务队列
                        self.image_queue.put({
                            'paragraph_context': copy.deepcopy(self._paragraph_context),
                            'min_context_len': min_context_len,
                            'delimiter_in_buffer': delimiter_in_buffer,
                            'fig_id': self.fig_id,
                            'output_line': new_output_line_old,
                        })
                        self.fig_id += 1
            # 轮询结果队列
            while not self.image_result_queue.empty():
                image_res = self.image_result_queue.get()
                if image_res != "no-image":
                    yield image_res
                self.image_result_queue.task_done()
        # Check remaining buffer after generator ends
        if "######" not in buffer and len(buffer) > 10:
            output_line_old = buffer

            finish_start, output_line, new_output_line_old = self.first_sentence_modification(
                finish_start, output_line_old, self.context.get_question(), delimiter_in_buffer)
            for c in output_line.strip():
                all_yielded_buffer += c
                yield c
            if delimiter_in_buffer == '\n':
                yield '<GraTAG type="image" id="{}"/>'.format(self.fig_id)
                yield '\n'
                # 将任务放入任务队列
                self.image_queue.put({
                    'paragraph_context': copy.deepcopy(self._paragraph_context),
                    'min_context_len': min_context_len,
                    'delimiter_in_buffer': delimiter_in_buffer,
                    'fig_id': self.fig_id,
                    'output_line': new_output_line_old,
                })
                self.fig_id += 1
            # 轮询结果队列
            while not self.image_result_queue.empty():
                image_res = self.image_result_queue.get()
                if image_res != "no-image":
                    yield image_res
                self.image_result_queue.task_done()
        # if still no-image, recall the fig-func
        log.debug("\n If still no-image, recall the fig-func!!")
        if self.fig_pos_id_since_last_time == 0:
            output_line_old = buffer
            yield '<GraTAG type="image" id="{}"/>'.format(self.fig_id)
            yield '\n'
            # 将任务放入任务队列
            self.image_queue.put({
                'paragraph_context': copy.deepcopy(self._paragraph_context),
                'min_context_len': min_context_len,
                'delimiter_in_buffer': delimiter_in_buffer,
                'fig_id': self.fig_id,
                'output_line': output_line_old + delimiter_in_buffer,
                'must': True
            })
            self.fig_id += 1
            # 轮询结果队列
            while not self.image_result_queue.empty():
                image_res = self.image_result_queue.get()
                if image_res != "no-image":
                    yield image_res
                self.image_result_queue.task_done()

        # if no output, output first sentence
        if len(all_yielded_buffer.replace(' ', '').replace('\n', '')) == 0:
            if len(self.first_sentence_repeated.strip()) > 0:
                output_line = self._add_ref_to_doc_line(self.first_sentence_repeated)
                for c in output_line:
                    yield c

        # 等待所有任务完成
        self.image_queue.put(None)
        worker_thread.join()
        self.image_queue.join()

        # 结束异步任务处理线程
        while True:
            try:
                image_res = self.image_result_queue.get()
            except queue.Empty:
                break
            if image_res is None:
                break
            if image_res != "no-image":
                yield image_res
            self.image_result_queue.task_done()
        ContextLogger(self.context).info(f"FINISH ALL text image functions！！！")

    def _call_query_answer(self, question: str, ref_content, n=1, **kwargs):
        mode = kwargs.get("mode", 'query_answer')
        # 载入预定义的PROMPT模版
        if mode in ["query_answer", "query_answer_quickpass"]:
            describe = "final问题回答"
        else:
            describe = "单个问题问答"
        model_name = self._get_model_name(mode, question)

        prompt_final = self._get_prompt(question, ref_content, **kwargs)
        ContextLogger(self.context).info(f"{describe} prompt:{prompt_final}, model: {model_name}")
        response = llm_call(
            query=prompt_final,
            model_name=model_name,
            temperature=0.0,
            n=n,
        )
        ContextLogger(self.context).info(f"{describe} response:{response}")
        if n == 1:
            response = [response]

        results = []
        results_raw = []
        for res_raw in response:
            answer_re, thought_re = self._decode_answer_from_llm_raw_output(res_raw)
            if answer_re:
                res = answer_re.group(1)
                results.append(res)
                results_raw.append(res_raw)
                if thought_re:
                    ContextLogger(self.context).info("参考大纲：{}".format(thought_re))
        if len(results_raw) == 0 and isinstance(response, list):
            results = response
            results_raw = response
        return results, prompt_final, results_raw

    def _add_paragraph_to_context(self, new_line):
        if new_line == '':
            return
        for paragraph in reversed(self._paragraph_context):
            if 'content' in paragraph:
                if paragraph['content'][-1] == '\n':
                    self._paragraph_context.append({
                        "type": "text",
                        "content": self._decode_no_markdown_answer_from_llm_raw_output(new_line),
                        "fig_pos_id": copy.deepcopy(self.fig_id)
                    })
                else:
                    paragraph['content'] += self._decode_no_markdown_answer_from_llm_raw_output(new_line)
                    paragraph['fig_pos_id'] = copy.deepcopy(self.fig_id)
                return
        self._paragraph_context.append({
            "type": "text",
            "content": self._decode_no_markdown_answer_from_llm_raw_output(new_line),
            "fig_pos_id": copy.deepcopy(self.fig_id)
        })


if __name__ == '__main__':
    from include.utils.skywalking_utils import trace_new, start_sw
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

    doc_answer = DocAnswer(
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







