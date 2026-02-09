from modules.pdf_extraction_group.pdf_extraction.pdf_process import pdf_process
from include.logger import ContextLogger
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import copy_current_request_context
from include.utils.skywalking_utils import trace_new
from include.decorator import timer_decorator

class PDFExtractGroup:
    """ pdf解析存储task
        必传入参:
            session_id = context.get_session_id()
    """
    def __init__(self, context):
        self.logger = ContextLogger(context)
        self.context = context

    @trace_new(op="get_intention")
    @timer_decorator
    def process(self, _ids: list, oss_ids: list, user_id: str, mode: str = "textonly", types: list = ['pdf']):
        self.logger.info(f"pdf extract begin, extract_mode is: {mode}, oss_ids: {oss_ids}")

        @copy_current_request_context
        def _pdf_process(_id, oss_id, user_id, mode, type_):
            res = pdf_process(_id, oss_id, user_id, mode, type_)
            return res

        with ThreadPoolExecutor(max_workers=len(oss_ids)) as executor:
            futures = [executor.submit(_pdf_process, _id, oss_id, user_id, mode, type_) for _id,oss_id,type_ in zip(_ids, oss_ids, types)]
        
        for future in as_completed(futures):
            try:
                result = future.result()
                self.logger.info(f"pdf extract result: {result}")
            except Exception as e:
                self.logger.error(f"pdf extract error: {e}")
        return 'finished'

if __name__ == '__main__':
    pdf_file_path = []
    PDFExtractGroup(pdf_file_path).process()