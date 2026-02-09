# coding:utf-8
# Answer Generation

import datetime
import sys, os

from include.utils.add_ref_to_doc import add_references_to_doc

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from include.utils.text_utils import get_other_content_sequential, get_DocQA_content, validate_and_filter_codes, get_md5
from include.config import PromptConfig
from include.context import DocQAContext
from include.logger import ContextLogger
from include.rag.search.query_all import is_valid_url
from include.utils.Igraph_utils import IGraph
from modules.query_answer_group.query_answer.answer_agent_AINews import DocAnswerAINews

QA2DocQA = {
    "query_simple_answer": "DocAnswerMix_SubAnswer",
    "query_answer": "DocAnswerMix_FinalAnswer",
    "query_answer_quickpass": "DocAnswerMixWithExample",
}


def get_chinese_date():
    # 获取今天的日期
    today = datetime.date.today()

    # 将日期格式化为中文格式：年-月-日
    chinese_format_date = today.strftime('%Y年%m月%d日')

    return chinese_format_date


class PDFDocAnswer(DocAnswerAINews):
    def __init__(
            self,
            question: str,
            references: dict,
            multi_hop_qa_dag: IGraph = None,
            max_try: int = 5,
            candidate_images: list = None,
            context:DocQAContext=None
    ):
        super().__init__(question, references, multi_hop_qa_dag, max_try, candidate_images, context)
        self.name = "PDFDocAnswer"
        self.context = context
        self.doc_name = self.context.get_doc_qa_pdf_names()
        self._top_n_indices = 100

    def _get_prompt(self, question, ref_content, **kwargs):
        ## 更新doc_mode 如果非指定doc相关模板，则根据速通非速通的三种模式做映射，映射到doc版本的三种模板。
        basemode = kwargs.get('mode')
        doc_mode = kwargs.get('doc_mode', "")
        ContextLogger(self.context).info("\n 当前回答阶段doc_mode状态：{}".format(doc_mode))
        if "Doc" not in doc_mode:
            doc_mode = QA2DocQA[basemode]
        raw_description = kwargs['raw_description'] 
        all_ref_items = kwargs['all_ref_items']

        def iterative_add_prompt(prompt_template):  # TODO 研报问答的模板需要迭代
            datestr = get_chinese_date()
            # 获取文档名字
            doc_name =""
            for idx, doc_item in enumerate(self.doc_name):
                doc_name += f"文档{idx + 1}的名称：{doc_item}\n"
            prompt_dic = {
                "query": question,
                "query_2": question,
                "ref_content": "",
                "date": datestr,
                "date_2": datestr,
                # "doc_name":doc_name,
                # "chart_understanding":""

            }
            pdf_ids = self.context.get_pdf_ids()
            prompt_dic.update({"related_QA": ""})
            # step1 初步加载
            prompt_init = prompt_template.format(**prompt_dic)

            # step2 搜索字数限制，筛选子问题问答信息
            related_QA = get_DocQA_content(
                prompt_init, self._multi_hop_qa_dag, self._max_input_tokens, doc_mode=doc_mode,
                is_answer_when_absent_ref=self.QAConfig['EXP_CONFIG']['is_answer_when_absent_ref'])
            prompt_dic.update({"related_QA": related_QA})

            # step3 添加图表信息
            ft_answer = self.context.get_figure_table_answer()
            if len(ft_answer) > 0:
                chart_understanding_list = [[] for _ in pdf_ids]
                for idx, ft_item in enumerate(ft_answer):
                    ft_item_ossid = ft_item["oss_id"]
                    ft_item_ossid_idx = pdf_ids.index(ft_item_ossid)
                    if ft_item["type"] == "figure":
                        caption = ft_item["caption"]
                        figure_answer = ft_item["ans"]
                        description = f"图表资料{idx}：图片标题：“{caption}”。图片描述：“{figure_answer}”"
                    elif ft_item["type"] == "table":
                        caption = ft_item["caption"]
                        table_answer = ft_item["ans"]
                        description = f"图表资料{idx}：表格标题：“{caption}”。表格内容：“{table_answer}”"
                    else:
                        description = ""
                    chart_understanding_list[ft_item_ossid_idx].append(description)
            else:
                chart_understanding_list = []
            # 加载子问题信息和图表信息
            prompt_init = prompt_template.format(**prompt_dic)
            # step4 搜索字数限制，筛选参考文献来源
            ref_content_list = get_other_content_sequential(prompt_init, ref_content, self._max_input_tokens,
                                                            raw_description, all_ref_items, pdf_ids)

            # 每个文档单独显示文件名、参考资料和图表
            ref_content_final = ""
            for i in range(len(pdf_ids)):
                # 统计名字
                tmp_pdf_name = self.doc_name[i]
                ref_content_final += f"文档{i + 1}的名称：{tmp_pdf_name}\n"
                # 统计参考资料
                if ref_content_list and len(ref_content_list)==len(pdf_ids):
                    tmp_ref_content = ref_content_list[i]
                    if tmp_ref_content:
                        ref_content_final += f"文档{i + 1}内容如下：\n"
                        ref_content_final += '\n'.join(tmp_ref_content) + '\n'
                # 统计图表信息
                if chart_understanding_list and len(ref_content_list)==len(pdf_ids):
                    tmp_chart_understanding_content = chart_understanding_list[i]
                    if tmp_chart_understanding_content:
                        tmp_chart_understanding_item_content = '\n'.join(tmp_chart_understanding_content)
                        ref_content_final += f"文档{i + 1}的图表信息如下：\n{tmp_chart_understanding_item_content}\n\n"
                # 不同文档间\n隔开
                ref_content_final+="\n"

            prompt_dic.update({"ref_content": ref_content_final})

            iterative_added_prompt = prompt_template.format(**prompt_dic)
            return iterative_added_prompt

        # 载入预定义的PROMPT模版
        if doc_mode in ["DocAnswerMix", "DocAnswerMixWithExample", "DocAnswerMix_SubAnswer", "DocAnswerMix_FinalAnswer"]:
            instruction_temp = PromptConfig[doc_mode]['instruction']
            prompt_final = iterative_add_prompt(instruction_temp)
        else:
            raise NotImplementedError
        prompt_final = prompt_final.replace('None', '无').replace('NONE', '无').replace('none', '无')
        return prompt_final

    def _add_ref_to_doc_line(self, answer):
        # 挂载reference, 并check格式
        answer = validate_and_filter_codes(answer)
        # 不对大小标题、带冒号的短句进行引证挂载
        if ("#" in answer or ("*" in answer and len(answer) < 10) or (':' in answer and len(answer) < 10) or
                ("：" in answer and len(answer) < 10)):
            return answer
        ref_dict = {}
        for each_ref in self.context.ref_answer:
            ref_dict[each_ref["_id"]] = {
                "id": get_md5(each_ref["content"]),
                "description": each_ref["content"]
            }
        final_ref_lib, final_answer = add_references_to_doc(ref_dict, answer, self.QAConfig, is_continue_ref=False)
        # TODO: 后续考虑图片的挂载
        # for final_ref_i in final_ref_lib.values():
        #     if isinstance(final_ref_i.get('other_info', dict()).get('images', list()), list):
        #         for image in final_ref_i['other_info']['images']:
        #             if image['url'] and image['url'] in self._candidate_lib:
        #                 self.ref_code_list.add(image['url'])
        return final_answer

    # 11月后可删除
    # def _streaming_output_find_final_answer(self, all_ref_items, question, use_for_check_items, mode='query_answer', add_title=False):
    #     ref_sentence = []
    #     raw_description = []
    #     for item_i, item in enumerate(all_ref_items):
    #         ref_publish_time = ""
    #         if is_valid_url(item["url"]):
    #             try:
    #                 raw_publish_time = datetime.datetime.strptime(item["other_info"]["publish_time"], "%Y-%m-%d %H:%M:%S")
    #                 ref_publish_time = "（发布于{}年{}月{}日）".format(raw_publish_time.year, raw_publish_time.month,
    #                                                                  raw_publish_time.day)
    #             except:
    #                 ref_publish_time = ""
    #         description = item["title"] + ref_publish_time + '：' + item["description"].replace("\r", " ").replace("\u3000", " ").replace(
    #             "\n",
    #             " ").strip() if (add_title and item['title'].strip() != '' and (item['title'].strip() != item['description'].strip())) else item["description"].replace("\r", " ").replace("\u3000", " ").replace(
    #             "\n",
    #             " ").strip()
    #         ref_sentence.append("资料{}".format(item_i) + ":" + description)
    #         raw_description.append(item['description'])
    #     ref_dict = self._references['use_for_check_items']

    #     ref_docs = set()
    #     for ref_i in ref_dict.values():
    #         ref_docs.add(ref_i['other_info']['doc_id'])
    #     ContextLogger(self.context).info("\n 准备开始流式输出！！！！ 待挂载的引证chunk个数：{}, 待挂载的引证doc个数：{}".format(
    #         len(ref_dict.keys()), len(ref_docs)
    #     ))
    #     return self._streaming_output_query_answer(
    #         question, ref_sentence, n=1, mode=mode, raw_description=raw_description, all_ref_items=all_ref_items)


if __name__ == '__main__':
    import time
    init_time = time.time()
