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

class DocInfoExtractTask():
    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.log = ContextLogger(self.context)
        self.log.info("callDocInfoExtract")
        self.query = self.context.get_question()     

    def get_doc_theme(self, **kwargs):
        pass

