# coding:utf-8
# Answer Generation
import datetime
import json
import traceback

from include.logger import log
from include.config import PromptConfig
from include.utils.llm_caller_utils import llm_call
from include.utils.text_utils import replace_multi_line_break, longest_common_substring
from include.utils.Igraph_utils import IGraph
from include.utils.add_ref_to_doc import add_references_to_doc
from modules.query_answer_group.query_answer.answer_agent_AINews import DocAnswerAINews
from modules.query_answer_group.query_answer.answer_agent import get_chinese_date
from include.decorator import timer_decorator


class GeneralDocAnswer(DocAnswerAINews):
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
        self.name = "GeneralDocAnswer"

    @timer_decorator
    def query_answer(self, single_hop=True, question_level=0, streaming=False):
        if question_level == 1:
            log.info("调用通用模型生成问题答案")
            return self._get_schedule_answer(streaming=streaming)
        else:
            log.info("调用RAG模型生成问题答案")
            if single_hop or not self._multi_hop_qa_dag:
                return self._call_single_hop_answer(streaming=streaming)
            else:
                return self._call_multi_hop_answer(streaming=streaming)

    def _get_optimized_references(self, is_filter=False):
        """
            对检索材料与问题进行相关有用性判断，返回筛选后的参考材料
            output:
            relevant_info_dict:{"id":"relevant_info"}
        """
        use_for_check_items_internet_all = self._references["use_for_check_items"]
        idx_list = []
        query_list = []
        use_for_check_items = dict()
        relevant_info_dict = dict()
        result_list = []
        for key, ref_info in use_for_check_items_internet_all.items():
            idx_list.append(key)
            relevant_info_dict[key] = {"description": ref_info["description"],
                                       "publish_time": ref_info["other_info"].get("publish_time", ""),
                                       "title": ref_info["other_info"].get("title", "")
                                       }
            if is_filter:
                # 获取材料发布时间
                ref_date = relevant_info_dict[key]["publish_time"]
                # 获取材料标题
                ref_title = relevant_info_dict[key]["title"]
                # 拼接材料信息
                ref_content = ""
                if ref_date is not None and len(ref_date) > 10:
                    ref_content += '材料发布日期：' + ref_date + '\n'
                if ref_title is not None and len(ref_title) > 6:
                    ref_content += '材料标题：' + ref_title + '\n\n'
                ref_content += relevant_info_dict[key]["description"]
                query_list.append(
                    PromptConfig["useful_reference"]["instruction"].format(
                        datetime.date.today().strftime('%Y年%m月%d日'), self._question, ref_content))
            else:
                result_list.append(str({"is_useful": True}))
        if is_filter:
            result_list = llm_call(query_list, self.QAConfig['TASK_MODEL_CONFIG']['useful_reference'], is_parallel=True,
                                   parallel_cnt=min(10, len(query_list)))
        relevant_info_list = []
        for i in range(len(result_list)):
            try:
                if result_list[i] is not None and isinstance(eval(result_list[i]), dict):
                    if eval(result_list[i])["is_useful"]:
                        relevant_info_list.append(relevant_info_dict[idx_list[i]])

                        # add to use_for_check_items
                        init_ref_info = use_for_check_items_internet_all[idx_list[i]]
                        source = self._source_dict.get(init_ref_info["source"], dict()).get("source", '')
                        source_name = self._source_dict.get(init_ref_info["source"], dict()).get("name", '')
                        use_for_check_items[idx_list[i]] = {
                            "id": init_ref_info.get("id"), "description": init_ref_info.get("description"),
                            "title": init_ref_info.get("title"),
                            "url": init_ref_info.get("url"), "source": source,
                            "source_id": init_ref_info.get("source_id"),
                            "other_info": init_ref_info.get("other_info", dict()),
                            "source_name": source_name,
                            "extract_relevant_info": result_list[i]
                        }
            except:
                continue
        log.info("get {} useful references from {} recall references.".format(len(relevant_info_list),
                                                                              len(use_for_check_items_internet_all)))
        return relevant_info_list, use_for_check_items

    def _build_ref_content(self, reference):
        try:
            relevant_info = []
            for ref_info in reference:
                relevant_info.append((ref_info["publish_time"],
                                      replace_multi_line_break(ref_info["description"]), ref_info["title"]))
            # 根据chunkDateStr, docId, chunkId排序参考材料
            sorted_relevant_info = sorted(relevant_info, key=lambda item: item[0], reverse=False)

            ref_content = ''

            for idx in range(len(sorted_relevant_info)):
                # 拼接材料标题
                if sorted_relevant_info[idx][2] is not None and len(sorted_relevant_info[idx][2]) > 6 and len(
                        longest_common_substring(sorted_relevant_info[idx][2],
                                                 sorted_relevant_info[idx][1])) < 0.5 * len(
                    sorted_relevant_info[idx][2]):
                    ref_content += "- " + sorted_relevant_info[idx][2] + "\n" + sorted_relevant_info[idx][1] + "\n\n"
                else:
                    ref_content += "- " + sorted_relevant_info[idx][1] + "\n\n"

            return ref_content
        except:
            return ""

    def _streaming_schedule_query_answer(self, instruction: str, ref_dict: dict):

        llm_output_generator = llm_call(
            query=instruction,
            model_name=self.QAConfig['TASK_MODEL_CONFIG']['general_query_answer'],
            max_tokens=len(instruction) + 1000,
            is_stream=True
        )
        return self._filter_generator(llm_output_generator)

    @timer_decorator
    def _get_schedule_answer(self, streaming=False):
        try:
            # 参考材料优选
            relevant_info_list, use_for_check_items = self._get_optimized_references()

            # 输入引证文本拼接
            ref_content = self._build_ref_content(relevant_info_list)

            assert len(ref_content) > 64, "No valid reference for answer generation."

            # 获取模型输入
            general_query_instruction = PromptConfig["general_query_answer"]["instruction"].format(
                get_chinese_date(), self._question, ref_content, get_chinese_date())
            #log.debug("llm input:{}".format(general_query_instruction))
            if streaming:
                return self._streaming_schedule_query_answer(general_query_instruction, use_for_check_items)
            else:
                init_answer = llm_call(query=general_query_instruction,
                                       model_name=self.QAConfig['TASK_MODEL_CONFIG']['general_query_answer'],
                                       max_tokens=len(general_query_instruction) + 1000)
                log.warning("init_answer:{}".format(init_answer))

                assert init_answer is not None, "No valid answer because of no valid output from large language model."

                # 引证标识后挂载
                used_ref, answer_with_ref = add_references_to_doc(use_for_check_items, init_answer, self.QAConfig)
                log.warning("answer_with_ref: {}".format(answer_with_ref))

                return {
                    "source": self.name,
                    "answer": answer_with_ref,
                    "input_llm": general_query_instruction,
                    "output_llm": init_answer,
                    "reference": used_ref,
                    "valid": True,
                    "message": ""
                }

        except Exception as e:
            traceback.print_exc()
            return {
                "source": self.name,
                "answer": "",
                "input_llm": "",
                "output_llm": "",
                "reference": "",
                "valid": False,
                "message": "{}".format(str(e))
            }


if __name__ == '__main__':
    import time

    init_time = time.time()
