import copy
import traceback
# import traceback
from functools import partial
from concurrent.futures import ThreadPoolExecutor
#from include.rag.tackle_with_search_item_utils import tackle_with_search_item_serial, generate_final_data_base
#from include.logger import log


DEFAULT_SIMI_DICT_FOR_ADDITION = {
    "sim2background_low": 0.40,
    "sim2background_high": 0.97,
    "sim2theme_low": 0.40,
    "sim2theme_high": 0.97,
    "sim2theme_sentence_level_low": 0.40,
    "sim2theme_sentence_level_high": 0.97,
}


class ReferenceController:
    def __init__(self):
        self._num_references = 0
        self._use_for_check_items = dict()
        self._use_for_check_items_content_dic = dict()
        self._use_for_check_items_opinion_similarity_dic = dict()
        self._fig_items = dict()
        self._origin_check_items = dict()

    def add(self, references):
        assert isinstance(references, dict), ""
        assert isinstance(references["use_for_check_items"], dict), ""
        assert isinstance(references["use_for_check_items_content_dic"], dict), ""
        assert isinstance(references["use_for_check_items_opinion_similarity_dic"], dict), ""

        assert (len(references["use_for_check_items"].keys()) ==
                len(references["use_for_check_items_content_dic"].keys()) ==
                len(references["use_for_check_items_opinion_similarity_dic"].keys())), "输入的证据不合法"
        new_use_for_check_items = references["use_for_check_items"]
        new_use_for_check_items_content_dic = references["use_for_check_items_content_dic"]
        new_use_for_check_items_opinion_similarity_dic = references["use_for_check_items_opinion_similarity_dic"]

        for key, value in new_use_for_check_items.items():
            content = value['description']
            if content not in self._use_for_check_items_content_dic:
                assert key not in self._use_for_check_items.keys(), "key not in self._use_for_check_items.keys()"
                self._num_references += 1
                self._use_for_check_items[key] = value
                self._use_for_check_items_content_dic[content] = key
                self._use_for_check_items_opinion_similarity_dic[content] = (
                    new_use_for_check_items_opinion_similarity_dic)[content]
            else:
                # 如果该内容已经存在过，那么需要更新simi dict
                assert key in self._use_for_check_items.keys(), "key in self._use_for_check_items.keys()"
                self._use_for_check_items_opinion_similarity_dic[content].update(
                    new_use_for_check_items_opinion_similarity_dic[content])

        assert (len(self._use_for_check_items.keys()) ==
                len(self._use_for_check_items_content_dic.keys()) ==
                len(self._use_for_check_items_opinion_similarity_dic.keys())), "添加证据后有问题产生！"

    def set_origin_ref(self, check_items):
        for key, value in check_items.items():
            if key not in self._origin_check_items.keys():
                self._origin_check_items[key] = copy.deepcopy(value)

    def get_origin_ref(self):
        return self._origin_check_items

    def add_fig(self, fig_data_base, application):
        if application not in self._fig_items:
            self._fig_items[application] = list()
        for fig in fig_data_base:
            if fig not in self._fig_items[application]:
                self._fig_items[application].append(fig)

    def get_check_items(self):
        return self._use_for_check_items

    def get_ref_code(self):
        return self._use_for_check_items_content_dic

    def get_similarity(self):
        return self._use_for_check_items_opinion_similarity_dic

    def get_all(self):
        return {
            "use_for_check_items": self._use_for_check_items,
            "use_for_check_items_content_dic": self._use_for_check_items_content_dic,
            "use_for_check_items_opinion_similarity_dic": self._use_for_check_items_opinion_similarity_dic
        }

    def get_fig(self, application):
        assert application in self._fig_items, "application must in self._fig_items"
        return self._fig_items[application]

    def get_ref_doc(self, need_new_content=False):
        res_dict = dict()
        for chunk_key, chunk_value in self._use_for_check_items.items():
            other_info = copy.deepcopy(chunk_value.get("other_info"))
            assert isinstance(other_info, dict), "other_info must be a dict"
            assert "doc_id" in other_info, "other_info must be a dict"
            doc_id = other_info['doc_id']
            if doc_id not in res_dict:
                ref_doc_content = ""
                if need_new_content:
                    for _, chunk_v in self._use_for_check_items.items():
                        if chunk_v.get('source_id') == doc_id:
                            ref_doc_content += chunk_v.get("description", "")
                res_dict[doc_id] = {
                    "_id": doc_id,
                    "url": chunk_value.get("url", ""),
                    "site": other_info.get("site", ""),
                    "title": chunk_value.get("title", ""),
                    "summary": other_info.get("query_keyword", ""),
                    "content": other_info.get("all_content", "") if not need_new_content else ref_doc_content,
                    "icon": other_info.get("icon", ""),
                    "all_info": other_info
                }
        return res_dict

    def get_ref_answer(self):
        res_list = []
        for chunk_key, chunk_value in self._use_for_check_items.items():
            other_info = chunk_value.get("other_info")
            assert isinstance(other_info, dict), "other_info must be a dict"
            assert "doc_id" in other_info, "other_info must be a dict"
            doc_id = other_info['doc_id']
            origin_content = []
            try:
                if chunk_value.get("other_info", dict()).get("origin_content"):
                    if chunk_value.get("other_info", dict()).get("origin_content", "") == "":
                        origin_content = [chunk_value.get("description", "")]
                    else:
                        origin_content = eval(chunk_value.get("other_info", dict()).get("origin_content", "[]"))
            except:
                origin_content = []
                traceback.print_exc()

            poly = []
            try:
                page_num_list = eval(chunk_value.get("other_info", dict()).get('page_num', '[]'))
                poly_list = eval(chunk_value.get("other_info", dict()).get('chunk_poly', '[]'))
                for page_num_i, poly_i in zip(page_num_list, poly_list):
                    poly.append(str(page_num_i) + ',' + str(poly_i).replace('[', '').replace(']', '').replace(' ', ''))
            except:
                poly = ['']
                traceback.print_exc()
            ref_answer_i = {
                "_id": chunk_value.get("id", ""),
                "news_id": doc_id,
                "content": chunk_value.get("description", ""),
                "origin_content": origin_content,
                "poly": poly
            }
            if chunk_value.get('other_info', dict()).get('oss_id', '') != '':
                ref_answer_i.update({"oss_id": chunk_value.get('other_info', dict()).get('oss_id', '')})
            res_list.append(ref_answer_i)
        return res_list

    def get_num_references(self):
        self._num_references = len(self._use_for_check_items.keys())
        return self._num_references

    def add_user_defined_ref(self, reference_list):
        self._user_defined_ref = reference_list

    def get_user_defined_reference_list(self):
        return self._user_defined_ref

    def update_reference_lib(self, question, query_info, user_references, batch_size: int = 128,
                             simi_dict=DEFAULT_SIMI_DICT_FOR_ADDITION):
        all_input_references = set()
        user_use_for_check_items_content_dic = dict()
        for user_reference_i in user_references:
            user_use_for_check_items_content_dic[user_reference_i['description']] = {
                "content": user_reference_i["description"],
                "blockContent": user_reference_i.get('blockContent', dict()),
                "title": user_reference_i.get('title', ''),
                "url": user_reference_i.get('url', ''),
                "source": user_reference_i.get('source', ''),
                "source_id": user_reference_i.get('source_id', ''),
                "theme": user_reference_i.get('theme', ''),
                "raw_input": user_reference_i.get('raw_input', ''),
                "otherinfo": user_reference_i.get('otherinfo', ''),
            }
            all_input_references.add(user_reference_i['description'])

        # 更新用户删除的数据
        current_lib_references = copy.deepcopy(self._use_for_check_items)
        # 遍历已有的数据库，如果不在用户输入中，就代表用户没有选择，将其删掉；
        # 如果在用户的输入中，就保留下来，并更新用户输入库（用户输入库仅保留用户添加的新数据）
        for key, value in current_lib_references.items():
            content = value['description']
            if content not in all_input_references:  # 如果不在用户输入中，就代表用户没有选择，将其删掉；
                self._num_references += 1
                self._use_for_check_items.pop(key)
                self._use_for_check_items_content_dic.pop(content)
                self._use_for_check_items_opinion_similarity_dic.pop(content)
            else:  # 如果在用户的输入中，就保留下来，并更新用户输入库（用户输入库仅保留用户添加的新数据）
                user_use_for_check_items_content_dic.pop(content)

        # 验证ref-lib有效
        assert (len(self._use_for_check_items.keys()) ==
                len(self._use_for_check_items_content_dic.keys()) ==
                len(self._use_for_check_items_opinion_similarity_dic.keys())), "更新证据库后有问题产生！ref-lib数据异常"

        addition_user_references = self.get_user_database(
            question, query_info, user_use_for_check_items_content_dic, simi_dict, batch_size)
        self.add(addition_user_references)
        return self.get_all()

    # def get_user_database(self, question, query_info, user_use_for_check_items_content_dic,
    #                       simi_dict, batch_size, sentence_similarity_bar=0.90):
    #     user_data_base = {
    #         "use_for_check_items": dict(),
    #         "use_for_check_items_content_dic": dict(),
    #         "use_for_check_items_opinion_similarity_dic": dict()
    #     }
    #     if len(user_use_for_check_items_content_dic.keys()) == 0:
    #         return user_data_base
    #
    #     simi_queries = copy.deepcopy(query_info['simi_queries'])
    #     if question not in query_info['simi_queries']:
    #         simi_queries.append(question)
    #
    #     # 添加用户更新的数据库
    #     res_all = self.addition_similarity(
    #         key_query=question, simi_queries=simi_queries,
    #         final_searched_items=list(user_use_for_check_items_content_dic.values()),
    #         simi_dict=simi_dict
    #     )
    #
    #     all_short_sentence_lines_origin = []
    #     for valid, res_tuple in res_all:
    #         if valid:
    #             try:
    #                 (_, _, all_short_sentence_lines_tmp, _, _, _, _, _) = res_tuple
    #                 for index, l in enumerate(all_short_sentence_lines_tmp):
    #                     all_short_sentence_lines_origin.append(l)
    #             except:
    #                 log.error(traceback.print_exc())
    #
    #     if len(all_short_sentence_lines_origin) == 0:
    #         return user_data_base
    #     else:
    #         # 数据库最终处理、存储
    #         (use_for_check_items, use_for_check_items_content_dic,
    #          use_for_check_items_opinion_similarity_dic) = generate_final_data_base(
    #             res_all, batch_size, sentence_similarity_bar=sentence_similarity_bar)
    #         user_data_base = {
    #             "use_for_check_items": use_for_check_items,
    #             "use_for_check_items_content_dic": use_for_check_items_content_dic,
    #             "use_for_check_items_opinion_similarity_dic": use_for_check_items_opinion_similarity_dic
    #         }
    #     return user_data_base
    #
    # def addition_similarity(self, key_query, simi_queries, final_searched_items, simi_dict):
    #     tackle_with_search_item_func = partial(
    #         tackle_with_search_item_serial,
    #         sep_short_sentence=self._is_sep_short_sentence,
    #         sep_text_length=self._sep_text_length,
    #         query=key_query,
    #         summary_recall="",
    #         valid_length=50,
    #         queries=simi_queries,
    #         simi_dict=simi_dict,
    #         llmCorr=False,
    #         mode="recall"
    #     )
    #
    #     num_pool = int(min(len(final_searched_items), 50))
    #     with ThreadPoolExecutor(max_workers=num_pool) as executor:
    #         # 使用 map 方法来并行执行函数
    #         res_all = list(executor.map(tackle_with_search_item_func, final_searched_items))
    #
    #     return res_all
