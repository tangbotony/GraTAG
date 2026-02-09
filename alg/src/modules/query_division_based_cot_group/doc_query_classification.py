import json
import time
import traceback
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.config import ModuleConfig
from include.logger import ContextLogger
from include.context import RagQAContext, RagQAReturnCode, DocQAContext
from include.utils.llm_caller_utils import llm_call
from include.decorator import timer_decorator



class DocQueryClassifyTask:
    def __init__(self, rag_qa_context: DocQAContext):
        self.context = rag_qa_context
        self.log = ContextLogger(self.context)
        self.log.info("callQueryClassifyTask")
        self.query = self.context.get_question()              # 用户输入的query

    @timer_decorator
    def query_classify(self):
        """
        对question做分类，综述问题 & 具体问题
        """
        try:
            model_name = ModuleConfig.light_model_name
            Classify_Template = ModuleConfig["DocQueryClassifyTemplate"] 
            prompt = Classify_Template.format(self.query)
            query_types = ModuleConfig.doc_query_types

            max_try = 3
            try_num = 0
            response = "具体问题"
            while try_num < max_try:
                try:
                    response = llm_call(
                            query=prompt,
                            model_name=model_name,  
                            n=1,             
                            temperature = 0.0,        # 通用拆分的temperature设置为0.0
                            )
                    for type_ in query_types:
                        if type_ in response:
                            response = type_
                            break
                    break
                except Exception as e:
                    try_num += 1
                    pass
            self.log.info(f"调用doc_query_classify对问题 '{self.query}' 分类结果为{response}")
            self.context.set_doc_query_type(response)

            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ""
        except Exception as e:
            self.log.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.UNKNOWN_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)

        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)


if __name__ == "__main__":
    from include.utils.text_utils import get_md5
    query = "请帮我做一个中国近7年GDP表格"
    # query = "假设你是著名的首席宏观经济分析师，请你仔细阅读这篇宏观研究报告，并写一篇1000字左右的总结。"
    context = DocQAContext(session_id=get_md5(query))
    context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
    DocQueryClassifyTask(context).query_classify()
    res = context.get_doc_query_type()
    print(res)