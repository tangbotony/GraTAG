# coding:utf-8
# 证据召回模块，对给定问题进行ES、Baidu等多路检索，构造证据库
import re
import copy
import json
import requests
import jieba #修改于2024年11月11日
from sklearn.feature_extraction.text import TfidfVectorizer #修改于2024年11月11日
from sklearn.metrics.pairwise import cosine_similarity #修改于2024年11月11日
import traceback
import numpy as np
from functools import partial
from include.logger import log
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.get_retrieval_range.get_retrieval_range_task import get_retrieval_range_func

from include.context.reference_controller import ReferenceController
from include.utils.time_utils import TimeCounter
from include.config import CommonConfig
from include.decorator import timer_decorator
from include.query_intent_recognition import get_reinforced_qkw
from include.utils.text_utils import get_search_keywords
from langchain_text_splitters import RecursiveCharacterTextSplitter
from include.rag.search.query_all import query_all
from include.utils.llm_caller_utils import llm_call
from include.rag.retrieval_utils import rerankBge
from include.utils.text_utils import generate_random_string


IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
rerank_config = CommonConfig['RERANK']

# embedding 配置
url = CommonConfig['FSCHAT']['general_url']
token = CommonConfig['AUTH_CONFIG']['key']
chunk_split_model = CommonConfig['CHUNK_SPLIT']['model']

# 检索域配置
SEARCH_FIELD_DEFAULT = copy.deepcopy({'iaar_database_kwargs': IAAR_DataBase_config['default_param']})

headers = {
    'token': token,
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}


def remove_html_tags(html):
    return re.sub(r'<[^>]+>', '', html)


def get_similarity_llm(
        queries: list, chunk_list: list,
        model_name='gpt-4o',
):
    try:
        llm_similarity_template = """你将被提供一个问题和一段材料，请判断材料信息是否有助于回答问题，如果有，则回答"true",否则返回"false"。
                问题: {query}
                材料: {chunk}

                注意，如果问题和材料的时间、人物等完全对不上，那么一定是false；
                如果两者虽然有差异，但这段材料一定程度上对于回答问题有帮助，比如问2024年中国GDP比2023年多多少，材料只谈了2023的GDP、没有谈2024年的，那就是true；
                如果材料中大段篇幅都谈的是于问题中实体无关的内容，比如问2024年中国GDP比2023年多多少，材料只谈了2021的GDP，那就是false；

                """

        def get_simi_i(query, chunk):
            try:
                prompt_dic = {
                    "query": query,
                    "chunk": chunk,
                }
                query_input = llm_similarity_template.format(**prompt_dic)
                res = llm_call(query_input, model_name=model_name, clog='', n=2 if model_name == 'gpt-4o' else 5)
                for relation_i in res:
                    try:
                        if re.search(r'\btrue\b', relation_i.strip(), re.IGNORECASE):
                            return 1
                        elif re.search(r'\bfalse\b', relation_i.strip(), re.IGNORECASE):
                            return 0
                    except:
                        print(traceback.format_exc())
                        continue
            except:
                print(traceback.format_exc())
                return 1
            return 0

        def process_query_chunk(pair):
            query_i, chunk_i = pair
            return get_simi_i(query_i, chunk_i)

        # 创建 query 和 chunk 的笛卡尔积
        query_chunk_pairs = [(query_i, chunk_i) for query_i in queries for chunk_i in chunk_list]

        # 使用 ThreadPoolExecutor 并行处理
        with ThreadPoolExecutor() as executor:
            similarity_scores = list(executor.map(process_query_chunk, query_chunk_pairs))

        # 将一维的 similarity_scores 转为二维的矩阵形式
        similarity_matrix = [
            similarity_scores[i * len(chunk_list):(i + 1) * len(chunk_list)]
            for i in range(len(queries))
        ]

        return {"response": similarity_matrix}
    except:
        return None


def get_similarity(queries: str, chunk_list: list):
    payload = json.dumps({
        "model": "bge_base_zh_embedding_sim_general",
        "params": {
            "request_id": "123",
            "text_a": [queries],
            "text_b": chunk_list
        }
    })

    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
        response.raise_for_status()
        result = json.loads(response.text)
        response.close()
        return result
    except requests.exceptions.RequestException as e:
        return None
    except json.JSONDecodeError as e:
        return None


def get_rerank(queries: str, chunk_list: list):
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))
    payload = json.dumps({
        "model": "bge_rerank_sft_webqa_ckpt2000_0823_rerank_infinity",
        "params": {
            "request_id": "123",
            "query": queries,
            "docs": chunk_list
        }
    })

    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
        response.raise_for_status()
        result = json.loads(response.text)
        response.close()
        results = np.array(result["response"])
        scores = sigmoid(results).tolist()
        result = {"response": [scores]}
        return result
    except requests.exceptions.RequestException as e:
        return None
    except json.JSONDecodeError as e:
        return None


def get_rerank_sft(queries: str, chunk_list: list, method: str):
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))
    if method == "rerank-sft":
        model = "bge_reranker_sft_gpt4o_ckpt1215_0827_rerank_infinity"
    elif method == "rerank-sft-0828":
        model = "reranker_sft_gpt4oupsamples_ckpt2988_0828_rerank_infinity"
    elif method == "rerank-sft-0829":
        model = "reranker_sft_rankdivide_ckpt3248_0829_rerank_infinity"
    else:
        raise NotImplementedError
    if not chunk_list:
        return None
    payload = json.dumps({
        "model": model,
        "params": {
            "request_id": "123",
            "query": queries,
            "docs": chunk_list
        }
    })

    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=7)
        response.raise_for_status()
        result = json.loads(response.text)
        response.close()
        results = np.array(result["response"])
        scores = sigmoid(results).tolist()
        result = {"response": [scores]}
        return result
    except requests.exceptions.RequestException as e:
        log.error("请reranker出错{}".format(traceback.format_exc()))
        return None
    except json.JSONDecodeError as e:
        return None


def get_rerank_base(queries: str, chunk_list: list):
    try:
        ans_rerank = rerankBge(queries, chunk_list, rerank_config, rerankModel="m3")
        result = {"response": [ans_rerank]}
        return result
    except requests.exceptions.RequestException as e:
        return None
    except json.JSONDecodeError as e:
        return None


def chunk_content(page_results: list, request_id: int, min_length=20):
    content_list = list()
    for page_result in page_results[:]:
        content = page_result.get('content')
        if content:
            content_list.append(content)
        else:
            page_results.remove(page_result)

    chunk_results = []
    split_content_list = split_doc_inteface_update_spliter(input_doc=content_list, request_id=request_id)
    for index, es_search in enumerate(page_results):
        for chunk in split_content_list.get(index, []):
            if len(chunk) > min_length:
                chunk_result = {key: val for key, val in es_search.items()}
                chunk_result.update({'chunk': chunk})
                chunk_results.append(chunk_result)
    return chunk_results


def split_doc_inteface(input_doc:list, splitter_flag=True, logger=None) -> dict:
    results = defaultdict(list)

    req = json.dumps({
        "model": "bge_base_zh_embedding_general",
        "params": {
            "request_id": "123",
            "batch_seq": input_doc,
            "text_splitter_config": {
                "splitter_type": "RecursiveCharacterTextSplitter",
                "only_splitter": splitter_flag,
                "RecursiveCharacterTextSplitter": {
                    "chunk_size": 350,
                    "chunk_overlap": 350*0.25
                }
            }
        }
    })

    if len(input_doc) > 0:
        try:
            response = requests.request("POST", url, headers=headers, data=req, timeout=5)
            result = json.loads(response.text)
            response.close()

            if isinstance(result, dict):
                logger.error(f'bge_base_zh model split inteface error, {result}')
                return results

            for item in result:
                results[item[0]].append(item[1])
        except requests.exceptions.RequestException as e:
            logger.error(f'HTTP request failed: {e}')
        except json.JSONDecodeError as e:
            logger.error(f'Failed to decode JSON response: {e}')
    return results


def Recursive_splitter(raw_text, request_id, chunk_size=300, overlap=300 * 0.2, chunk_max_size=2000, method='new_server'):
    if method == 'base':
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=overlap, length_function=len, is_separator_regex=False, keep_separator="end",
            separators=["\n\n", "\n", "。", "？", " ", ",", "\u200b", ""]
        )

        texts = text_splitter.create_documents([raw_text])
        ans = []
        for text in texts:
            ans.append(text.page_content)
    elif method == 'new_server':
        payload = json.dumps({
            "model": chunk_split_model,
            "params": {
                "request_id": request_id,
                "batch_seq": [raw_text],
                "text_splitter_config": {
                    "splitter_type": "Recursive",
                    "only_splitter": True,
                    "Recursive": {
                        "chunk_size": chunk_size,
                        "chunk_overlap": int(overlap),
                        "chunk_max_size": chunk_max_size
                    },
                }
            }
        })
        headers = {
            'token': token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        texts = eval(response.text)
        ans = []
        for text in texts:
            try:
                text_json = json.loads(text[1])
                ans.append(text_json['chunk'])
            except:
                log.warning("{} not a json".format(text))
    else:
        raise NotImplementedError
    return ans


def split_doc_inteface_update_spliter(input_doc: list, request_id: int, splitter_flag=True, logger=None) -> dict:
    results = defaultdict(list)
    if len(input_doc) == 0:
        return results

    def process_element(index, doc):
        return index, Recursive_splitter(doc, request_id)

    with ThreadPoolExecutor() as executor:
        future_to_index = {executor.submit(process_element, i, doc): i for i, doc in enumerate(input_doc)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                idx, result = future.result()
                results[idx].extend(result)
            except Exception as exc:
                if logger:
                    logger.error(f'Doc {index} generated an exception: {exc}')
    return results


def get_domain_from_query(domain: str):
    """
    :param domain: （可能）带域名的检索词
    :return: 去除域名的检索词
    """
    domain = domain.split("site:")[0]  # 去除最后的url限制信息
    domain = re.sub(r'\s+$', '', domain)  # 去除不必要的空格
    return domain


class RagRecall:
    def __init__(
            self,
            user_info: dict,  # 模块调用方信息
            query: str,  # 待检索的query词
            logger,  # 日志
            search_field: dict = SEARCH_FIELD_DEFAULT,
            credible='false',
            auto_router_source='true',  # 是否自动指定检索源
            query_reinforce=False,  # 是否问题增强
            max_try: int = 3,  # 最大尝试次数,
            max_query_reinforce: int = 5,  # 问题增强最大个数
            similarity_config=None,  # 判断query-chunk相似度的配置
            retrieval_range=None,  # 指定的检索词
            auto_retrieval_range=False,  # 自动为query添加识别检索区间
            min_num_chunks: int = 3,  # 即使不相关，也至少应该返回这些检索材料
            chunk_min_length: int = 20,  # 最小的chunk大小
            max_chunk: int = 60,  # 最多返回max_chunk个chunk
            pro_flag: bool = True,
            use_raw_ranker: bool = True
    ):
        # basic
        self.name = "RagRecall"
        self._user_info = user_info
        self._query = query
        self._logger = logger
        self._max_try = max_try
        self._credible = credible
        self._auto_router_source = auto_router_source
        self._query_reinforce = query_reinforce
        self._query_kwargs = copy.deepcopy(search_field)
        self._max_query_reinforce = max_query_reinforce
        self._retrieval_range = retrieval_range
        self._auto_retrieval_range = auto_retrieval_range
        self._min_num_chunks = min_num_chunks
        self._chunk_min_length = chunk_min_length
        self._max_chunk = max_chunk
        self._pro_flag = pro_flag
        self._use_raw_ranker = use_raw_ranker

        if not similarity_config:
            self._similarity_config = {
                "method": 'rerank-sft-0829',
                "is_filter": True,
                "simi_bar": 0.80,
                "model_name": 'gpt-4o',
                "top_n": 30,
            }
        else:
            self._similarity_config = similarity_config

        # ref_data_base_related
        self._data_base = dict()
        self._candidate_images = list()

        # time related
        self._time = TimeCounter()
        self._time_task_name = "RagRecallTask"
        self._time.add_task(self._time_task_name)

        # RecallHARDCODE!!!!
        self._word_list = ['今天', '今天', '今日', '明天', '明日', '昨天', '昨日', '前天', '后天', '年', '月', '日',
                           '上周', '上一周', '本周', '这周', '这一周', '本月', '这个月', '上个月', '新闻', '有', '什么', '的']

    def _router(self):
        """
            检索方式分发，对于不同的query，指定不同的数据源
        """
        news_type = 0
        if 'iaar_database_kwargs' in self._query_kwargs:
            body = self._query_kwargs['iaar_database_kwargs']

            # 触发榜单检索 在有明确起止日期的情况下，都可以通过榜单通道来直接获取这段日期内的材料
            chinese_query = re.sub(r'[^\u4e00-\u9fa5]', '', self._query)
            for word in self._word_list:
                chinese_query = chinese_query.replace(word, '')

            route = body['online_search'] if 'online_search' in body else body
            if len(chinese_query) <= 1 and ('start_date' in route):
                log.debug("触发榜单检索!!!")
                body.update({"queries": ""})
                body.update({"return_num": IAAR_DataBase_config['hot_news_count']})
                body.update({"start_date": route['start_date']})
                body.update({"end_date": route['end_date']})
                news_type = 'hot_news'

            # 触发新闻检索
            elif "新闻" in self._query and "keywords" in body:
                log.debug("触发新闻检索!!!")
                body.update({"queries": body['keywords']})
                del body['keywords']
                if 'bing_field' in route:
                    route['bing_field']['switch'] = True
                    route['bing_field']['type'] = 'news'
                # 关闭百度和搜索
                if 'sogou_field' in route:
                    route['sogou_field']['switch'] = False
                if 'baidu_field' in route:
                    route['baidu_field']['switch'] = False
                news_type = 'news'
            self._query_kwargs['iaar_database_kwargs']['news_type'] = news_type

    @timer_decorator
    def _get_reinforced_rag_query(self):
        # 增强的问题
        rag_queries = [self._query]
        if self._query_reinforce:
            reinforced_questions = get_reinforced_qkw(self._query)
            if reinforced_questions:
                for reinforced_question in reinforced_questions:
                    if reinforced_question != self._query:
                        rag_queries.append(reinforced_question['question'])
        rag_queries = list(set(rag_queries))[:self._max_query_reinforce]
        return rag_queries

    @timer_decorator
    def _generate_final_database(self, final_searched_items: list):
        use_for_check_items = dict()  # {'$key': docDic}  **
        use_for_check_items_content_dic = dict()  # {'$content': key} **
        use_for_check_items_opinion_similarity_dic = dict()  # {'$content': {query: similarity}}

        doc_list = []
        key_list = []
        content_info_list = []
        for search_item in final_searched_items:
            content_tmp = search_item.get('chunk', '')  # 该引证的内容
            if content_tmp in use_for_check_items_content_dic:
                continue
            content_key = "[%s]" % generate_random_string(content_tmp, 8)
            content_info = {
                'id': content_key,
                'description': content_tmp,
                'title': search_item.get('title', ''),
                'url': search_item.get('url', ''),
                'source': search_item.get('source', ''),
                'source_id': search_item.get('source_id', ''),
                'other_info': search_item.get("otherinfo", dict()),
                'rerank_score': search_item.get("score", ''),
                'raw_input': search_item.get("otherinfo", dict()).get("query_input", '')
            }
            doc_list.append(content_tmp)
            key_list.append(content_key)
            content_info_list.append(content_info)

        for chunk_i, chunk_key_i, chunk_info_i in zip(doc_list, key_list, content_info_list):
            if chunk_i not in use_for_check_items_opinion_similarity_dic:
                use_for_check_items_opinion_similarity_dic[chunk_i] = {}
            use_for_check_items_opinion_similarity_dic[chunk_i][chunk_info_i.get(
                'chunk_info_i', dict()).get("query_input", '')] = chunk_info_i.get('rerank_score', 1.0)
            chunk_info_i.get('other_info', dict())['score'] = chunk_info_i.get('rerank_score', 1.0)
            use_for_check_items[chunk_key_i] = chunk_info_i
            use_for_check_items_content_dic[chunk_i] = chunk_key_i
        return {
            "use_for_check_items": use_for_check_items,
            "use_for_check_items_content_dic": use_for_check_items_content_dic,
            "use_for_check_items_opinion_similarity_dic": use_for_check_items_opinion_similarity_dic
        }

    @timer_decorator
    def _add_retrieval_range(self, retrieval_range):
        #  嵌入时间窗
        for retrieval_field_name, retrieval_field_kwargs in self._query_kwargs.items():
            if retrieval_field_name == 'iaar_database_kwargs':
                retrieval_field_kwargs['request_id'] = self._user_info['session_id']
                # 嵌入关键词
                if 'keywords' in retrieval_range and len(retrieval_range['keywords']) > 0:
                    retrieval_field_kwargs['keywords'] = ' '.join(retrieval_range['keywords'])

                # 嵌入时间窗
                if 'online_search' in retrieval_field_kwargs:
                    route = retrieval_field_kwargs['online_search']
                else:
                    route = retrieval_field_kwargs
                if 'start_time' in retrieval_range and len(retrieval_range['start_time']) > 0:
                    route['start_date'] = retrieval_range['start_time']
                    if 'end_time' in retrieval_range and len(retrieval_range['end_time']) > 0:
                        route['end_date'] = retrieval_range['end_time']

    @timer_decorator
    def construct_database(self):
        """
        : param: queries
        """
        # 自动添加retrieval_range
        if self._auto_retrieval_range and not self._retrieval_range:
            retrieval_range = get_retrieval_range_func(self._query, self._query, self._user_info['session_id'])
            self._add_retrieval_range(retrieval_range)
        if self._retrieval_range:
            retrieval_range = self._retrieval_range
            self._add_retrieval_range(retrieval_range)

        # 自动匹配检索源
        if self._auto_router_source:
            self._router()

        # 问题增强
        rag_queries = [self._query]
        if self._query_reinforce:
            rag_queries = self._get_reinforced_rag_query()

        # 多路检索及去重
        log.debug("待检索的原query：{}, 问题增强后用于检索的queries: {}".format(self._query, rag_queries))
        searched_items = self._call_multi_reference(core_query=self._query, rag_queries=rag_queries)

        # chunk分片
        chunk_searched_items = self._split_chunks(searched_items)

        # 粗排序模型，先用tf-idf法
        if self._use_raw_ranker:
            log.debug("use raw ranker!!")
            chunk_searched_items = self.sort_by_tf_idf(chunk_searched_items)

        #keywords和综合方法的调用代码
        #chunk_searched_items = self.sort_by_keywords(chunk_searched_items)
        #chunk_searched_items = self.sort_combined_v1(chunk_searched_items)

        # 相似chunk过滤
        if self._pro_flag:
            related_chunks = self._chunk_rank(chunk_searched_items)
        else:
            related_chunks = list()
            for key, results in chunk_searched_items.items():
                related_chunks.extend(results)

        self._add_candidate_images(related_chunks)
        log.debug("检索返回chunk数量: {}".format(len(related_chunks)))

        # 整理最终检索到的材料
        reference = ReferenceController()
        references_data_base = self._generate_final_database(related_chunks)
        if references_data_base:
            reference.add(references_data_base)
        log.debug("过滤后的chunk数量:{}".format(reference.get_num_references()))
        self._data_base = reference.get_all()

    def get_data_base(self):
        return self._data_base

    def get_images_data_base(self):
        return self._candidate_images

    def set_data_base(self, data_base: dict):
        assert "use_for_check_items" in data_base and "use_for_check_items_content_dic" in data_base and \
               "use_for_check_items_opinion_similarity_dic" in data_base
        self._data_base = data_base

    def _add_candidate_images(self, final_searched_items):
        num_candidate_image = 0
        for ref in final_searched_items:
            if isinstance(ref.get('otherinfo', dict()).get('images', list()), list):
                for image in ref['otherinfo']['images']:
                    image['origin_doc_url'] = ref['url']
                    image['title'] = ref.get('otherinfo', dict()).get('title', '')
                    image['all_content'] = ref.get('otherinfo', dict()).get('all_content', '')
                    image['search_word'] = ref.get('raw_input', '')
                    image['height'] = image.get('high', None)
                    image['width'] = image.get('width', None)
                    image['origin_img_url'] = image.get('url', None)
                    self._candidate_images.append(image)
                    num_candidate_image += 1
        log.debug("In total {} searched_items, finally find {} images".format(
            len(final_searched_items), num_candidate_image))

    @timer_decorator
    def _call_multi_reference(self, core_query: str, rag_queries: list):
        """
        :param
            core_query: 上游业务传入的检索词
            call_ref_source_query: 多路检索
        :return:
            final_searched_items: 保存为list的形式，平铺存储检索的信息
            final_searched_items_theme: 保存为字典的形式，分主题存储检索的信息
        """
        final_searched_items = []
        i_try = 0
        while len(final_searched_items) == 0 and i_try < self._max_try:
            final_searched_items = []  # 保存为list的形式，平铺存储检索的信息
            all_content_all_url = set()  # 所有的检索结果去重

            log.warning("正在并行检索{}个query, 分别是：{}".format(len(rag_queries), rag_queries))
            # 开始做并发请求
            query_multi_source_partial_func = partial(
                self._call_single_reference,
                core_query=core_query
            )

            with ThreadPoolExecutor(max_workers=20) as executor:
                all_result = list(executor.map(query_multi_source_partial_func, rag_queries))

            for i, result_refs in enumerate(all_result):
                for item in result_refs:
                    all_content_all_url.add(item['content'])
                    final_searched_items.append(item)
            if len(final_searched_items) == 0:
                log.warning("检索未召回，try：{}/{}".format(i_try + 1, self._max_try))
                i_try += 1
        if len(final_searched_items) <= 0:
            log.warning("没有成功的找到检索资源！！！！！！！")
        return final_searched_items

    @timer_decorator
    def _call_single_reference(self, query_input: str, core_query: str):
        final_references = []
        # 检索query词摘要
        if len(query_input) < 60:
            query_abstract = query_input.strip()
        else:
            # query_abstract = ' '.join(get_search_keywords(query_input[:60]))
            query_abstract = ' '.join(query_input[:60])
            log.debug("检索词{}太长，改为：{}".format(query_input, query_abstract))

        # TODO: 用户可以指定core_query是否走summary直连检索逻辑
        # if query_input == context.get_question() and "iaar_database_kwargs" in self._query_kwargs.keys():
        #     self._query_kwargs['iaar_database_kwargs']["online_search"]["bing_field"]["type"] = "page"

        references = query_all(query_abstract, user_info=self._user_info, query_kwargs=copy.deepcopy(self._query_kwargs),
                               pro_flag=self._pro_flag, topk=self._max_chunk)[0]
        for reference in references:
            try:
                content = reference["content"]
                content = remove_html_tags(content)
                reference.update({
                    "content": content,
                    "otherinfo": {"author": reference.get("author"),
                                  "title": reference.get("title"),
                                  "publish_time": reference.get("publish_time"),
                                  "images": reference.get("images"),
                                  "source": reference.get("source"),
                                  "type": reference.get("type"),
                                  "url": reference.get("url"),
                                  "source_id": reference.get("source_id"),
                                  "score": reference.get("score"),
                                  "region": reference.get("region"),
                                  "doc_id": reference.get("source_id"),
                                  "docId": reference.get("source_id"),
                                  "icon": reference.get("icon", ''),
                                  "query_abstract": query_abstract,
                                  "query_input": query_input,
                                  "all_content": content,
                                  "chunk_num": reference.get("chunk_id"),
                                  "chunk_poly": reference.get("chunk_poly", '[]'),
                                  "origin_content": reference.get("origin_content"),
                                  "oss_id": reference.get("oss_id"),
                                  "user_id": reference.get("user_id"),
                                  "page_num": reference.get("page_num", '[]')
                                  }
                })
                final_references.append(reference)
            except Exception as e:
                log.error("reference:{}".format(reference))
                traceback.print_exc()
                log.error("没有查到证据对应的来源库！跳过此条证据！")
        return final_references

    @timer_decorator
    def _split_chunks(self, searched_items: list):
        max_chunk = self._max_chunk
        online_chunk_list: list = chunk_content(searched_items, request_id=self._user_info['request_id'],
                                                min_length=self._chunk_min_length)
        chunk_searched_items = {
            'online': online_chunk_list[:max_chunk],
            'es': list(),
            'embedding': list()
        }
        log.info("In module {}, 分片后，有{}个chunk".format(self.name, len(online_chunk_list[:max_chunk])))
        return chunk_searched_items

    @timer_decorator
    def _chunk_rank(self, chunk_searched_items):
        core_query = self._query
        unranked_results_list = list()
        method = self._similarity_config.get("method", "base")
        is_filter = self._similarity_config.get("is_filter", True)
        simi_bar = self._similarity_config.get("simi_bar", 0.5)
        model_name = self._similarity_config.get("model_name", "gpt-4o")
        top_n = self._similarity_config.get("top_n", 30)

        if method == 'base':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('chunk', ''))
            response = get_similarity(core_query, chunk_list)
        elif method == 'llm':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                # TODO: delete this
                results = results[:50]
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('title', '') + ':' + res.get('chunk', ''))
            response = get_similarity_llm([core_query], chunk_list, model_name=model_name)
        elif method == 'rerank':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('title', '') + ':' + res.get('chunk', ''))
            response = get_rerank(core_query, chunk_list)
        elif method == 'rerank-sft':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('title', '') + ':' + res.get('chunk', ''))
            response = get_rerank_sft(core_query, chunk_list, method=method)
        elif method == 'rerank-sft-0828':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('title', '') + ':' + res.get('chunk', ''))
            response = get_rerank_sft(core_query, chunk_list, method=method)
        elif method == 'rerank-sft-0829':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('title', '') + ':' + res.get('chunk', ''))
            response = get_rerank_sft(core_query, chunk_list, method=method)
        elif method == 'rerank_base':
            chunk_list = list()
            for key, results in chunk_searched_items.items():
                unranked_results_list.extend(results)
                for res in results:
                    chunk_list.append(res.get('title', '') + ':' + res.get('chunk', ''))
            response = get_rerank_base(core_query, chunk_list)
        else:
            log.error("rank chunk method must be in base or llm!!!")
            return unranked_results_list[:top_n]
        if response:
            sim_list = response.get('response')[0]

            if len(sim_list) != len(unranked_results_list):
                return unranked_results_list[:top_n]

            new_ranked_results_list = copy.deepcopy(unranked_results_list)
            # 确保 'otherinfo' 是独立的对象
            for item in new_ranked_results_list:
                item['otherinfo'] = copy.deepcopy(item['otherinfo'])
            for index, new_ranked_results_list_i in enumerate(new_ranked_results_list):
                new_ranked_results_list_i.update({'score': sim_list[index]})
                new_ranked_results_list_i['otherinfo']['score'] = sim_list[index]

            if is_filter:
                ranked_result = sorted(
                    [item for item in new_ranked_results_list if (item['score'] and item['score'] > simi_bar)],
                    key=lambda x: x['score'],
                    reverse=True
                )
            else:
                ranked_result = sorted(new_ranked_results_list, key=lambda x: x['score'], reverse=True)

            # 如果过滤后的chunk数太少，则取top self._min_num_chunks
            if len(ranked_result) <= self._min_num_chunks:
                ranked_result = sorted(new_ranked_results_list, key=lambda x: x['score'], reverse=True
                                       )[:self._min_num_chunks]
                log.warning("检索到的chunk数过少！！取top{}".format(self._min_num_chunks))
            log.info("In module {}, 相关度过滤后，有{}个chunk".format(self.name, len(ranked_result)))
            return ranked_result[:top_n]
        else:
            return unranked_results_list[:self._min_num_chunks]

    def call_source(self):
        # 自动匹配检索源
        if self._auto_router_source:
            self._router()

        # 问题增强
        rag_queries = [self._query]
        if self._query_reinforce:
            rag_queries = self._get_reinforced_rag_query()

        # 多路检索及去重
        log.debug("待检索的原query：{}, 问题增强后用于检索的queries: {}".format(self._query, rag_queries))
        searched_items = self._call_multi_reference(core_query=self._query, rag_queries=rag_queries)
        return searched_items

    def call_chunk_split(self, searched_items):
        # chunk分片
        chunk_searched_items = self._split_chunks(searched_items)
        return chunk_searched_items

    #测试更新的函数 2024年11月12日
    # 根据问题中有多少keyword出现在chunk里面的比例
    # 计算的相似度，再根据计算出来的相似度从检索来的chunk之中选出default为最好60个的chunk。
    def sort_by_keywords(self,chunk_searched_items,result_key="online",top_k=60):
        unranked_results_list=chunk_searched_items[result_key]
        retrieval_range = get_retrieval_range_func(self._query, self._query, self._user_info['session_id'])
        #匹配关键词合集
        keywords = retrieval_range['character']+retrieval_range['location']+retrieval_range['keywords']+retrieval_range['keyword_all']
        #print('keyword_all   ',retrieval_range['keyword_all'])
        num_keywords=len(keywords)
        if num_keywords==0:
            print('没有keywords产出！！')
            return unranked_results_list[:top_k]
        #scores=[]
        for index, item in enumerate(unranked_results_list):
            chunk = item['chunk']
            cnt_match = 0#多少个匹配关键词在分片里面
            for keyword in keywords:
                if keyword in chunk:
                    cnt_match=cnt_match+1
            match_score = cnt_match/num_keywords
            item.update({'keyword score': match_score})
            #scores.append(match_score)
        ranked_result = sorted(unranked_results_list, key=lambda x: x['keyword score'], reverse=True)
        chunk_searched_items[result_key] = ranked_result[:top_k]
        return chunk_searched_items
    #根据tf-idf计算的相似度进行粗排序，再根据计算出来的相似度从检索来的chunk之中选出default为最好60个的chunk。
    def sort_by_tf_idf(self,chunk_searched_items,result_key="online",top_k=60):
        unranked_results_list=chunk_searched_items[result_key]
        #scores=[]
        for index, item in enumerate(unranked_results_list):
            chunk = item['chunk']
            lis1=list(jieba.cut(self._query))
            lis2=list(jieba.cut(chunk))
            txt1=' '.join(lis1)
            txt2=' '.join(lis2)
            vectorizer = TfidfVectorizer()
            vectorizer.fit([txt1,txt2])
            tfidf_1=vectorizer.transform([txt1])
            tfidf_2=vectorizer.transform([txt2])
            similarity_matrix = cosine_similarity(tfidf_1,tfidf_2)
            sim_score = similarity_matrix[0][0]
            item.update({'tf-idf score': sim_score})
            #scores.append(sim_score)
        ranked_result = sorted(unranked_results_list, key=lambda x: x['tf-idf score'], reverse=True)
        chunk_searched_items[result_key] = ranked_result[:top_k]
        return chunk_searched_items
    #把上面tf-idf的分数和根据keyword的相似度分数结合平均一下，再用平均后分数作为排序依据
    #选出default数量为前60的chunks
    def sort_combined_v1(self,chunk_searched_items,result_key="online",top_k=60):
        #--计算关键词分数
        unranked_results_list=chunk_searched_items[result_key]
        retrieval_range = get_retrieval_range_func(self._query, self._query, self._user_info['session_id'])
        #匹配关键词合集
        keywords = retrieval_range['character']+retrieval_range['location']+retrieval_range['keywords']+retrieval_range['keyword_all']
        #print('keyword_all   ',retrieval_range['keyword_all'])
        num_keywords=len(keywords)
        #原问题有keywords，就按照chunks里面出现keywords数量/问题里面总keywords数量得出keywords
        #分数，原问题没提取出keywords，就通通按照分数0来算。
        if num_keywords==0:
            print('没有keywords产出！！')
            for index, item in enumerate(unranked_results_list):
                item.update({'keyword score': 0.0})
        else:
            for index, item in enumerate(unranked_results_list):
                chunk = item['chunk']
                cnt_match = 0#多少个匹配关键词在分片里面
                for keyword in keywords:
                    if keyword in chunk:
                        cnt_match=cnt_match+1
                match_score = cnt_match/num_keywords
                item.update({'keyword score': match_score})
        
        #计算tf_idf分数
        for index, item in enumerate(unranked_results_list):
            chunk = item['chunk']
            lis1=list(jieba.cut(self._query))
            lis2=list(jieba.cut(chunk))
            txt1=' '.join(lis1)
            txt2=' '.join(lis2)
            vectorizer = TfidfVectorizer()
            vectorizer.fit([txt1,txt2])
            tfidf_1=vectorizer.transform([txt1])
            tfidf_2=vectorizer.transform([txt2])
            similarity_matrix = cosine_similarity(tfidf_1,tfidf_2)
            sim_score = similarity_matrix[0][0]
            item.update({'tf-idf score': sim_score})
        
        for index, item in enumerate(unranked_results_list):
            try:
                comb_score = (item['keyword score']+item['tf-idf score'])/2
                item.update({'combined score': comb_score})
            except:
                print('error, lacking one of scores for average')
        ranked_result = sorted(unranked_results_list, key=lambda x: x['combined score'], reverse=True)
        chunk_searched_items[result_key] = ranked_result[:top_k]
        return chunk_searched_items

        
    def call_chunk_rank(self, chunk_searched_items):
        # 相似chunk过滤
        related_chunks = self._chunk_rank(copy.deepcopy(chunk_searched_items))

        self._add_candidate_images(related_chunks)
        log.debug("检索返回chunk数量: {}".format(len(related_chunks)))

        # 整理最终检索到的材料
        reference = ReferenceController()
        references_data_base = self._generate_final_database(related_chunks)
        if references_data_base:
            reference.add(references_data_base)
        log.debug("过滤后的chunk数量:{}".format(reference.get_num_references()))
        self._data_base = reference.get_all()
        return self._data_base


if __name__ == '__main__':
    import time
    IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
    pro_flag = True
    # {
    #     'file_database_kwargs': {
    #         "search_type": ["online"],
    #         "doc_id": ["pdf-source-file/外乱内稳下的资产配置-兴业证券宏观.pdf",
    #                    ]
    #     },
    #     # 'iaar_database_kwargs': IAAR_DataBase_config['default_param']
    # }
    if pro_flag:  # pro版
        search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param']}
    else:
        search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param_pro_flag']}
    queries = [
        # "对2020年第四季度安徽省第一产业增加值进行数据解读",
        # "安徽怀远今天发生了什么",
        # "有什么关于美国的新闻？",
        # "有什么关于以色列的新闻？",
        # "甘肃积石山地震受灾情况如何？",
        # "当前美国总统是谁？"
        # '美国巴黎奥运会每个项目分别得了多少个金牌'
        '请分析2024年以来，有关新质生产力的报道情况'
    ]

    if pro_flag:  # pro版
        search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param']}
    else:
        search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param_pro_flag']}
    queries = [
        # "对2020年第四季度安徽省第一产业增加值进行数据解读",
        # "安徽怀远今天发生了什么",
        # "有什么关于美国的新闻？",
        # "有什么关于以色列的新闻？",
        # "甘肃积石山地震受灾情况如何？",
        # "当前美国总统是谁？"
        # '美国巴黎奥运会每个项目分别得了多少个金牌'
        '请分析2024年以来，有关新质生产力的报道情况'
    ]
#   原始的测试内容，注释2024年11月11日
    # {
    #     'file_database_kwargs': {
    #         "search_type": ["online"],
    #         "doc_id": ["pdf-source-file/外乱内稳下的资产配置-兴业证券宏观.pdf",
    #                    ]
    #     },
    #     # 'iaar_database_kwargs': IAAR_DataBase_config['default_param']
    # }


    for query_i in queries:
        my_rag_recall = RagRecall(
            user_info={
                'application': 'GraTAG',
                'session_id': "test_rag_recall_session_id",
                'question_id': "test_rag_recall_question_id",
                'request_id': time.time()
            },
            query=query_i, logger=log, search_field=copy.deepcopy(search_field),
            credible='false', auto_router_source='false',
            query_reinforce=False,
            similarity_config={
                "method": 'rerank_base',  # base/llm/rerank/rerank_base
                "is_filter": True,
                "simi_bar": 0.0,
                "model_name": 'gpt-4o',
                "top_n": 30
            },
            auto_retrieval_range=False,
            min_num_chunks=0,
            pro_flag=pro_flag,
            max_chunk=300,
            chunk_min_length=20
        )
        my_rag_recall.construct_database()
        data_base_i = my_rag_recall.get_data_base()
        fig_data_base_i = my_rag_recall.get_images_data_base()
        for ref_index, ref_i in enumerate(data_base_i.get('use_for_check_items', dict()).values()):
            print("{}- | TITLE: {} | BROADCAST TIME: {} | CHUNK: {}".format(
                ref_index,
                ref_i['title'],
                ref_i['other_info']['publish_time'],
                ref_i['description']
            ))