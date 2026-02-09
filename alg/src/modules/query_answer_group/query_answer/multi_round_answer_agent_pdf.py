# coding:utf-8
# Multi-Round Answer Generation
from include.logger import ContextLogger
from include.config import PromptConfig
from include.utils.Igraph_utils import IGraph
from include.utils.llm_caller_utils import llm_call
from include.utils.dialog_util import Dialogue
from modules.query_answer_group.query_answer.answer_agent_pdf import PDFDocAnswer


class MultiRoundPDFDocAnswer(PDFDocAnswer):
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
        self.name = "MultiRoundPDFDocAnswer"
        self._doc_mode = 'DocAnswerMixWithExample'

    def _get_messages(self, prompt_final, mode='query_answer_multi_round'):
        prompt_template_multi_round = PromptConfig[mode]['instruction']
        dialogue = Dialogue()
        history_dialogue = self.context.get_dialog()
        for index, dialogue_i in enumerate(list(history_dialogue.values())[:-1]):
            if index == 0:
                dialogue.add_conversation('system', prompt_template_multi_round)
            question_i = dialogue_i.get_question()
            answer_i = dialogue_i.get_answer()
            if isinstance(question_i, str) and len(question_i.strip()) == 0:
                answer_i = ""
            dialogue.add_conversation('user', question_i)
            dialogue.add_conversation('assistant', answer_i)
        dialogue.add_conversation('user', prompt_final)
        return dialogue

    def _streaming_output_query_answer(self, question: str, ref_content, n=1, mode='query_answer', fig=True, **kwargs):
        model_name = self._get_model_name(mode, question)
        prompt_final = self._get_prompt(question, ref_content, mode = mode, **kwargs)
        messages = self._get_messages(prompt_final)
        ContextLogger(self.context).info(f"最终问题回答 prompt:{prompt_final}, model: {model_name}")
        ContextLogger(self.context).info(f"最终问题回答 messages:{messages.print_conversations()}, model: {model_name}")
        llm_output_generator = llm_call(
            query=messages,
            model_name=model_name,
            is_stream=True,
            temperature=0.0
        )
        self.context.add_sft_info({
            "mode": mode,
            "llm_input": prompt_final
        })
        return self._filter_generator(llm_output_generator)

    def _call_query_answer(self, question: str, ref_content, n=1, **kwargs):
        mode = kwargs.get("mode", 'query_answer')
        # 载入预定义的PROMPT模版
        if mode in ["query_answer", "query_answer_quickpass"]:
            describe = "final问题回答"
        else:
            describe = "单个问题问答"
        model_name = self._get_model_name(mode, question)

        prompt_final = self._get_prompt(question, ref_content, **kwargs)
        messages = self._get_messages(prompt_final)
        ContextLogger(self.context).info(f"{describe} prompt:{prompt_final}, model: {model_name}")
        ContextLogger(self.context).info(f"{describe} messages:{messages.print_conversations()}, model: {model_name}")
        response = llm_call(
            query=messages,
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


if __name__ == '__main__':
    import time
    init_time = time.time()
