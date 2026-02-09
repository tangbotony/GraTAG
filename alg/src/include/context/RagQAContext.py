import copy
import string
import pickle
import base64
import time
from collections import OrderedDict

from include.logger import ContextLogger
from include.context.reference_controller import ReferenceController
from include.context.QuesionType import QuesionType
from include.config import CommonConfig
IAAR_DataBase_config = CommonConfig['IAAR_DataBase']

DEFAULT_JSON = {
    "character": [],
    "location": [],
    "keywords": [],
    "start_time": "",
    "end_time": ""
}


class RagSingleQA:

    def __init__(self, session_id, request_id, question_id, question, pro_flag=True):
        self._session_id = session_id
        self._request_id = request_id
        self._question_id = question_id
        self._question = question

        self._origin_question = question
        self._question_time_test = None
        self._answer = None
        self._retrieval_range = DEFAULT_JSON
        self._reference = ReferenceController()
        self._is_command = False
        self._finish_query_ir = False   # 是否完成意图识别接口的调用
        self._question_rejection = {"is_reject": False}   # {"is_reject":True/False, "reject_reason":"xx"},  # 问题拒答判断结果
        self._question_supplement = {"is_supply": False}  # {"is_supply":True/False, "supply_description":"xx","supply_choices":["xx", "xx", ....]}  # 问题补充判断结果
        self._further_recommend = [] #追问问题
        self._retrieval_field = {
            'iaar_database_kwargs': copy.deepcopy(IAAR_DataBase_config['default_param'])
        }
        # 检索召回

        self._multi_hop_rag_queries = None
        self._task_type = None  
        self._general_dag = None
        self._timeline_dag = None
        self._reinforced_questions = None
        self._supply_info = {"is_supply": False, "supply_info":[]}   # {"is_supply": true/false, "supply_info":["xx","xx","xx"]}
        self._question_zh = question   # 对全英问题的中文翻译结果
        self._related_event = ""  # 判断输入问题是否与特定事件相关联, 如果与特定事件相关联，self._related_event为对应事件，否则为""
        self._timeline_rewrite_query = {"is_timeline_query":False ,"dimension":"","timeline_queries":[]} #原问题改写为时间线问题
        self._timeline_new_query=""
        self._timeline_sort_events = None  # 时间线流程中事件去重和排序结果
        self._timeline_highlight_events = []    # 时间线流程中highlight提取结果
        self._granularity = None  # 用户对时间线问题指定的展示粒度
        self._timeline_reference = {} # 时间线生成检索回的reference
        self._timeline_chunk_reference = {}  # 时间线生成检索回的reference
        self._question_type = 0 #
        self._rewrite_appendix_info = None
        self._is_ref_recall_finished_flag = False
        self._quickpass = False
        self._sft_info_list = list()  # 大模型存储的sft数据
        self._final_answer_list = []
        self._pro_flag = pro_flag
        self._llm_finalinput = ""

    def get_pro_flag(self):
        return self._pro_flag

    def get_question_type(self):
        return self._question_type

    def set_question_type(self, question_type:QuesionType):
        self._question_type = question_type

    def get_origin_question(self):
        return self._origin_question

    def set_origin_question(self,question):
        self._origin_question=question

    def get_question(self):
        return self._question

    def set_question(self,question):
        self._question=question

    def get_question_id(self):
        return self._question_id

    def get_request_id(self):
        return self._request_id
    
    def set_QA_quickpass(self):
        self._quickpass = True

    def get_QA_quickpass(self):
        return self._quickpass

    def set_rewrite_appendix_info(self, appendix_info):
        self._rewrite_appendix_info = appendix_info
        
    def get_rewrite_appendix_info(self):
        return self._rewrite_appendix_info

    def set_question_time_test(self, question_time):
        self._question_time_test = question_time

    def get_question_time_test(self):
        return self._question_time_test

    def set_answer(self, answer):
        self._answer = answer

    def get_answer(self):
        return self._answer

    def set_supply_info(self, supply_info):
        self._supply_info = supply_info

    def get_supply_info(self):
        return self._supply_info

    def set_retrieval_range(self, retrieval_range):
        self._retrieval_range = retrieval_range

    def get_retrieval_range(self):
        return self._retrieval_range

    def set_question_supplement(self, question_supplement):
        self._question_supplement = question_supplement

    def get_question_supplement(self):
        return self._question_supplement

    def set_question_rejection(self, question_rejection):
        self._question_rejection = question_rejection

    def get_reinforced_questions(self):
        return self._reinforced_questions

    def set_related_event(self, related_event):
        self._related_event = related_event

    def get_related_event(self):
        return self._related_event

    def set_finish_query_ir(self, finish_flag):
        self._finish_query_ir = finish_flag

    def get_finish_query_ir(self):
        return self._finish_query_ir

    def set_task_type(self, type_):
        self._task_type = type_

    def get_task_type(self):
        return self._task_type

    def set_general_dag(self, dag):
        self._general_dag = dag

    def get_general_dag(self):
        return self._general_dag

    def set_timeline_dag(self, dag): 
        self._timeline_dag = dag

    def get_timeline_dag(self):
        return self._timeline_dag

    def get_question_zh(self):
        return self._question_zh

    def set_question_zh(self, question_zh):
        self._question_zh = question_zh

    def get_question_rejection(self):
        return self._question_rejection

    def set_retrieval_field(self, retrieval_field):
        self._retrieval_field = retrieval_field

    def get_retrieval_field(self):
        return self._retrieval_field

    def add_references_result(self, references):
        self._reference.add(references)

    def add_fig_result(self, figures, application):
        self._reference.add_fig(figures, application)

    def get_fig_result(self, application):
        return self._reference.get_fig(application)

    def get_references_result(self):
        return self._reference.get_all()

    def get_references_result_doc(self, need_new_content=False):
        return self._reference.get_ref_doc(need_new_content)

    def get_origin_ref(self):
        return self._reference.get_origin_ref()

    def set_origin_ref(self, check_items):
        self._reference.set_origin_ref(check_items)

    def get_ref_answer(self):
        # 将检索结束标置为True
        self._is_ref_recall_finished_flag = True
        return self._reference.get_ref_answer()

    def set_recall_finished_flag(self, ref_recall_finished_flag):
        self._is_ref_recall_finished_flag = ref_recall_finished_flag

    def get_recall_finished_flag(self):
        return self._is_ref_recall_finished_flag

    def reset_reference(self):
        self._reference = ReferenceController()

    def set_multi_hop_rag_queries(self, multi_hop_rag_queries):
        self._multi_hop_rag_queries = multi_hop_rag_queries

    def get_multi_hop_rag_queries(self):
        return self._multi_hop_rag_queries
    
    def set_is_command_question(self, is_command):
        self._is_command = is_command
    
    def get_is_command_question(self):
        return self._is_command
    
    def set_further_recommend_questions(self, further_recommend):
        self._further_recommend = further_recommend
    
    def get_further_recommend_questions(self):
        return self._further_recommend

    def set_reinforced_questions(self, reinforced_questions):
        self._reinforced_questions = reinforced_questions

    def get_reinforced_questions(self):
        return self._reinforced_questions
    
    def set_timeline_rewrite_query(self,timeline_rewrite_query):
        self._timeline_rewrite_query = timeline_rewrite_query

    def get_timeline_rewrite_query(self):
        return self._timeline_rewrite_query

    def set_timeline_new_query(self,timeline_new_query):
        self._timeline_new_query = timeline_new_query

    def get_timeline_new_query(self):
        return self._timeline_new_query
    def set_timeline_sort_events(self,timeline_sort_events):
        self._timeline_sort_events=timeline_sort_events

    def get_timeline_sort_events(self):
        return self._timeline_sort_events

    def set_timeline_highlight_events(self,timeline_highlight_events):
        self._timeline_highlight_events=timeline_highlight_events

    def get_timeline_highlight_events(self):
        return self._timeline_highlight_events

    def set_granularity(self, granularity):
        self._granularity = granularity

    def get_granularity(self):
        return self._granularity

    def set_timeline_reference(self, timeline_reference):
        self._timeline_reference = timeline_reference

    def get_timeline_reference(self):
        return self._timeline_reference

    def set_timeline_chunk_reference(self, timeline_chunk_reference):
        self._timeline_chunk_reference = timeline_chunk_reference

    def get_timeline_chunk_reference(self):
        return self._timeline_chunk_reference

    def add_sft_info(self, sft_info):
        self._sft_info_list.append(sft_info)

    def get_sft_info(self):
        return self._sft_info_list

    def set_final_answer_list(self, final_answer_list):
        self._final_answer_list = final_answer_list

    def get_final_answer_list(self):
        return self._final_answer_list

    def set_llm_final_input(self, llm_final_input):
        self._llm_finalinput = llm_final_input

    def get_llm_final_input(self):
        return self._llm_finalinput

class RagQAContext:
    # @trace_new()
    def __init__(self,
                 session_id: string,
                 user_id: string = ''
                 ):
        """
        创建一个context对象
        :param session_id: 会话ID
        :param request_id: 请求ID
        }
        """
        self._session_id = session_id  # 会话id, str
        self._user_id = user_id
        self._request_id = None  # 请求id, str
        self._cur_question_id = None  # 当前问题
        self._dialog = OrderedDict()  # 会话历史
        self._basic_user_info = {"User_Date":time.time(), "User_IP":"39.99.228.188"}    # 传入形式是字符串 {"User_Date":"1716465070.90962", "User_IP":"39.99.228.188"}
        self._recommend_questions = [] #推荐的问题
        self._recommend_query = [] #query补全
        self._user_id = user_id

    def get_user_id(self):
        return self._user_id

    def set_session_id(self, session_id):
        self._session_id = session_id

    def get_session_id(self):
        return self._session_id

    def set_QA_quickpass(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_QA_quickpass()

    def get_QA_quickpass(self, question_id = None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        if_quickpass = rag_single_qa.get_QA_quickpass()
        return if_quickpass

    def set_basic_user_info(self, user_info):
        self._basic_user_info = user_info

    def get_basic_user_info(self):
        return self._basic_user_info

    def add_single_question(self, request_id, question_id, question, pro_flag=True):
        self._dialog[question_id] = RagSingleQA(self._session_id, request_id, question_id, question, pro_flag)
        self._cur_question_id = question_id

    def get_single_question(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa

    def get_origin_question(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        question = rag_single_qa.get_origin_question()
        return question
    
    def set_origin_question(self, question, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_origin_question(question)
    
    def get_question(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        question = rag_single_qa.get_question()
        return question

    def get_request_id(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        request_id = rag_single_qa.get_request_id()
        return request_id

    def get_question_id(self):
        return self._cur_question_id

    def get_dialog(self):
        return self._dialog

    def set_question_time_test(self, question_time, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_question_time_test(question_time)

    def get_question_time_test(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_question_time_test()

    def set_supply_info(self, supply_info, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_supply_info(supply_info)

    def get_supply_info(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_supply_info()

    def set_related_event(self, related_event, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_related_event(related_event)

    def get_related_event(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_related_event()

    def set_finish_query_ir(self, finish_flag, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_finish_query_ir(finish_flag)

    def get_finish_query_ir(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_finish_query_ir()

    def set_answer(self, final_answer, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_answer(final_answer)

    def get_answer(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_answer()

    def set_task_type(self, task_type, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_task_type(task_type)

    def get_task_type(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_task_type()

    def set_dag(self, dag, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_general_dag(dag)

    def get_dag(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_general_dag()
    
    def set_timeline_dag(self, dag, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_timeline_dag(dag)

    def get_timeline_dag(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_dag()

    def set_retrieval_range(self, retrieval_range, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_retrieval_range(retrieval_range)

    def get_retrieval_range(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_retrieval_range()

    def add_references_result(self, references, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.add_references_result(references)

    def add_fig_result(self, figures, application, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.add_fig_result(figures, application)

    def get_fig_result(self, application, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_fig_result(application)

    def get_references_result(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_references_result()

    def get_references_result_doc(self, question_id=None, need_new_content=False):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_references_result_doc(need_new_content)

    def set_origin_ref(self, check_items, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_origin_ref(check_items)

    def get_origin_ref(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_origin_ref()

    def get_ref_answer(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_ref_answer()

    def set_question_supplement(self, question_supplement, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_question_supplement(question_supplement)

    def get_question_supplement(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_question_supplement()

    def set_question_zh(self, question_zh, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_question_zh(question_zh)

    def set_rewrite_appendix_info(self, appendix_info, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_rewrite_appendix_info(appendix_info)

    def get_rewrite_appendix_info(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_rewrite_appendix_info()

    def set_question(self, question, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_question(question)

    def get_question_zh(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_question_zh()

    def set_question_rejection(self, question_rejection, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_question_rejection(question_rejection)

    def get_question_rejection(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_question_rejection()

    def set_retrieval_field(self, set_retrival_field, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_retrieval_field(set_retrival_field)

    def get_retrieval_field(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_retrieval_field()

    def reset_reference(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.reset_reference()

    def set_multi_hop_rag_queries(self, multi_hop_rag_queries, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_multi_hop_rag_queries(multi_hop_rag_queries)

    def get_multi_hop_rag_queries(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_multi_hop_rag_queries()

    def set_is_command_question(self, is_command, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_is_command_question(is_command)

    def get_is_command_question(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_is_command_question()
    
    def set_recommend_questions(self, recommend_questions):
        self._recommend_questions = recommend_questions

    def get_recommend_questions(self):
        return self._recommend_questions

    def set_recommend_query(self, recommend_query):
        self._recommend_query = recommend_query

    def get_recommend_query(self):
        return self._recommend_query
    
    def set_further_recommend_questions(self, further_recommend, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_further_recommend_questions(further_recommend)
    
    def get_further_recommend_questions(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_further_recommend_questions()
    
    def get_history_questions(self, del_current_query = False):
        history_questions = []
        if self._dialog:
            for question_id, rag_single_qa in self._dialog.items():
                history_questions.append(rag_single_qa.get_question())
        if del_current_query:
            history_questions = history_questions[:-1]
        return history_questions

    def set_reinforced_questions(self, reinforced_questions, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_reinforced_questions(reinforced_questions)

    def get_reinforced_questions(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_reinforced_questions()
    
    def set_timeline_rewrite_query(self, timeline_rewrite_query,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_timeline_rewrite_query(timeline_rewrite_query)
    
    def get_timeline_rewrite_query(self,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_rewrite_query()

    def set_timeline_new_query(self, timeline_new_query, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_timeline_new_query(timeline_new_query)

    def get_timeline_new_query(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_new_query()

    def set_timeline_sort_events(self, timeline_sort_events,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_timeline_sort_events(timeline_sort_events)

    def get_timeline_sort_events(self,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_sort_events()

    def set_timeline_highlight_events(self, timeline_highlight_events,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_timeline_highlight_events(timeline_highlight_events)

    def get_timeline_highlight_events(self,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_highlight_events()

    def set_granularity(self, granularity, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_granularity(granularity)

    def get_granularity(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_granularity()

    def set_timeline_reference(self, timeline_reference, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_timeline_reference(timeline_reference)

    def get_timeline_reference(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_reference()

    def set_timeline_chunk_reference(self, timeline_chunk_reference, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_timeline_chunk_reference(timeline_chunk_reference)

    def get_timeline_chunk_reference(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_timeline_chunk_reference()

    def get_question_type(self,question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_question_type()

    def set_question_type(self, question_type:QuesionType, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_question_type(question_type)

    def set_recall_finished_flag(self, ref_recall_finished_flag, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_recall_finished_flag(ref_recall_finished_flag)

    def get_recall_finished_flag(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_recall_finished_flag()

    def add_sft_info(self, sft_info: dict, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.add_sft_info(sft_info)

    def get_sft_info(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_sft_info()

    def set_final_answer_list(self, final_answer_list, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_final_answer_list(final_answer_list)

    def get_final_answer_list(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_final_answer_list()

    def set_llm_final_input(self, llm_final_input, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_llm_final_input(llm_final_input)

    def get_llm_final_input(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_llm_final_input()



# 序列化并编码
def context_encode(obj: RagQAContext):
    serialized = pickle.dumps(copy.deepcopy(obj), protocol=pickle.HIGHEST_PROTOCOL)
    return base64.b64encode(serialized).decode("utf-8")


# 解码并反序列化
def context_decode(serialized_str) -> RagQAContext:
    decoded_bytes = base64.b64decode(serialized_str)
    return pickle.loads(decoded_bytes)


if __name__ == '__main__':
    from include.utils.es_utils import save_to_es, load_from_es
    data = load_from_es({
        "query": {
            "bool": {
                "must": [
                    {"match": {"session_id": 432}}
                ]
            }
        },
        "size": 10  # Limit the number of returned documents to 1000
    }, es_name="ES_QA", index_name="default")
    decoded_context = context_decode(data)
    print(data)

    contextaaaaa = RagQAContext("?", user_id="mock_user_id")
    contextaaaaa.add_single_question(1, 2, "。。。???", pro_flag=True)
    contextaaaaa.add_references_result({'use_for_check_items': {'[YzbNJ0Qg]': {'id': '68d1c4b603293a21fd3b680fe2e1c636c97ef59db004d893a97c78c29a4e3e1e', 'description': '他亲口承认了包括玫瑰战争在内的诸多历史事件影响了他的写作过程,并最终反映到了小说之中,但是他亦坚持道:“书中并没有严格意义上的一对一关系,我更喜欢把历史当成一种调剂品,使得奇幻小说变得更加真实可靠,但绝不会简单地换个名字就挪到我的作品里面。”《冰与火之歌》中的多条情节线索和人物设定都与历史上的“玫瑰战争”相暗合,小说的两个主要家族:史塔克与兰尼斯特,分别代表了历史上的约克家族与兰开斯特家族。', 'title': '冰与火之歌(乔治·R·R·马丁所著小说) - 百度百科', 'url': 'https://baike.baidu.com/item/%E3%80%8A%E5%86%B0%E4%B8%8E%E7%81%AB%E4%B9%8B%E6%AD%8C%E3%80%8B/15415', 'theme': '冰与火之歌小说系列的故事背景是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[9EeAZjyr]': {'id': '250c77cdff2d30c78448b28d3fcac7914c728ba0da12a39c94e89eb1e445e308', 'description': '美剧 《冰与火之歌》 主要描述了在一片虚构的中世纪世界里所发生的一系列宫廷斗争、疆场厮杀、游历冒险和魔法抗衡的故事。《冰与火之歌》的故事发生在一个虚幻的中世纪世界,主要目光集中在西方的“日落王国”维斯特洛大陆 上,讲述那里的人在当时的政治背景下的遭遇和经历。第一条主线围绕着各方诸侯意图问鼎整个王国的权力中心 铁王座 而进行“权力的游戏”王朝斗争的故事展开。', 'title': '《冰与火之歌》主要讲了一个什么故事? - 百度知道', 'url': 'https://zhidao.baidu.com/question/1700240719689535908.html', 'theme': '冰与火之歌小说系列的故事主线是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[lBpKtwrS]': {'id': '089f219088d31b5ae5bb307e31cf7b641c674756b49890ed7951a844ec29da92', 'description': '扩展资料 《权力的游戏》,是美国 HBO电视网 制作推出的一部中世纪史诗奇幻题材的电视剧。该剧改编自美国作家 乔治·R·R·马丁 的奇幻小说《冰与火之歌》系列。《权力的游戏》以“创造奇迹”的高姿态打破了魔幻剧难以取得成功的美剧“魔咒”,一举颠覆所有好莱坞魔幻电影的创意水平。', 'title': '《冰与火之歌》主要讲了一个什么故事? - 百度知道', 'url': 'https://zhidao.baidu.com/question/1700240719689535908.html', 'theme': '冰与火之歌小说系列的故事主线是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[KZICqZGs]': {'id': 'f5dfebd7a49176a0f76739d5bd06e52367323fc02a3cbf9d3e68d5fb29b31176', 'description': '它给予演员、导演、编剧创意的无限可能,以其无限且有序的创作空间囊括了成千上万形象饱满的人物角色、怪诞独特充满想象的风土人情,其空间之完整、细节之丰富、叙事之恣意让人感叹。《冰与火之歌》是由美国作家乔治·R·R·马丁所著的严肃奇幻小说系列。该书系列首卷于1996年初由矮脚鸡图书公司在美国出版,全书计划共七卷,截至2014年共完成出版了五卷,被译为三十多种文字。', 'title': '《冰与火之歌》主要讲了一个什么故事? - 百度知道', 'url': 'https://zhidao.baidu.com/question/1700240719689535908.html', 'theme': '冰与火之歌小说系列的故事主线是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[2mMEVLs7]': {'id': '2822fbbd27d9267c4fcb0f346437f58a842aef5f8982224ca9acfe90accea150', 'description': '乔治·R.R·马丁  如果你是《权力的游戏》或者原著《冰与火之歌》的粉丝，一定听说了作者乔治·R.R·马丁史诗般的新作《火与血》出版了。《火与血》讲述了《权利的游戏》里坦格利安家族的历史，是此系列的第一卷。虽然在2013年的时候，马丁曾计划等这一系列全部完成后再出版，但后来还是决定先出个两卷本。', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[OVyT4zTx]': {'id': '598e25d030a0b0470957de1b564014badf558bbfb9917f5e6a01a75d40758450', 'description': '《火与血》英文版《冰与火之歌》改变的《权力的游戏》自2011年4月17日在美国HBO电视台首次播出以来，迎来连续多年的收视狂潮，在全世界赢得了无数忠实粉丝，2015年第67届艾美奖中破纪录地斩获12项大奖之后，今年又获得2018年第70届艾美奖最佳剧集奖。将于2019年4月播出的该系列第八季让很多人翘首以盼。如今《火与血》的出版，我们是不是又可以期待新作品的中文版引进，以及电视剧改编了呢？', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[x8T0Ogqg]': {'id': '8886849fcd6d419ea7978fefab2a2f660915dcb839514f9fcd0aaeae4493318c', 'description': '《火与血》描写的是《权游》中维斯特洛大陆的故事300年之前的事情。尽管差了几个世纪，然而根据最近马丁接受《娱乐周刊》（Entertainment Weekly）的采访来看，《火与血》中埋了一些关于《冰与火之歌》的小暗示。”确实有一些重要的小线索，不过我不会透露太多，读者必须自己去找出它们，然后辨别那些到底真的是暗示还是不过为了转移注意力的把戏。“马丁这样说。', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[qzY1q7J4]': {'id': 'f13d2ca9259530a58573cacc84c5fb70dda4faff24151c532084e219ed5e9a94', 'description': '我必须写完才行。“你都这么可爱地自责了，我们当然不会催你啦。马丁说《火与血》这本书对他来说是个很大的安慰，因为坦格利安家族系列完全是自己写出来的。很多人可能不太了解，此前的《冰与火之歌》是马丁和另一个作者伊莱奥·M·加西亚 Jr.合作写出，而这将是完全属于马丁自己的作品，是不是很期待呢？', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[C3c2k1s0]': {'id': '2578e904d8850e9b57037c82ef9de039d20ced87a857c7f1fa2cb241b82783da', 'description': '新客立减 登录 《冰与火之歌》主要情节 《冰与火之歌》是一部由美国作家乔治 · R· R· 马丁创作的史诗奇 幻小说系列,共有五卷。本书以中世纪为背景,讲述了七个王国 之间的权力斗争、家族恩怨以及古老的神秘力量的觉醒。以下是 《冰与火之歌》主要情节的梗概。第一卷:《权力的游戏》 本卷主要围绕斯塔克家族展开。史塔克家族是北境的贵族家族,由埃德 · 史塔克领导。', 'title': '《冰与火之歌》主要情节 - 百度文库', 'url': 'https://wenku.baidu.com/view/1c064f7f7a563c1ec5da50e2524de518974bd362.html', 'theme': '冰与火之歌小说系列的主要事件是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[cvbxsXlw]': {'id': '6a80f50753338326472c62d838743552382394c2082cc2def43aec4f67dc7cfc', 'description': '在这个充满快餐文化的时代，我们渴望着一些能够让我们陶冶情操、感受深刻的故事。而《冰与火之歌》（冰与火之歌）这本作品无疑是能够满足我们这种需求的经典之作。这本书集奇幻、政治、战争、爱情、背叛等元素于一身，讲述了一个虚构的中世纪欧洲风格的世界，探讨了人性、道德和权力的主题，给我们带来了一个充满惊喜和震撼的阅读体验。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[aJLxh2CK]': {'id': 'a63a8f2d35441e6c04a9696eeeee4972d1de495ef7fe5071de6e98d501f835fc', 'description': '在这个世界里，冰雪覆盖的北境、温暖宜人的南方、狂风肆虐的铁群岛、险峻的狭海、神秘的东方大陆等等，都成为了故事的背景。而书中许多角色也成为了经典，包括奈德·史塔克、提利昂·兰尼斯特、琼恩·雪诺、丹妮莉丝·坦格利安等等。他们的经历被交织在一起，构成了一个庞大而精致的史诗。《冰与火之歌》的故事情节复杂而精彩，这也是其最为吸引人的地方之一。在这个世界里，人人都有自己的目的和野心，都在为争夺铁王座而努力。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[CErsrEqh]': {'id': 'd9a230e5c840ef911c05b225790995bdacbcd4b914be1c3768fd331e20aa7933', 'description': '身为诸侯之一的奈德·史塔克，却在一场与势力更大的家族兰尼斯特的斗争中意外地失去了自己的生命。他的儿子罗柏成为了北方的领袖，并承诺要为他的父亲复仇。同时，南方的兰尼斯特家族也在为掌握铁王座而斗争，不惜手段地谋杀敌对家族的成员，包括国王。整个故事的发展都充满着政治斗争、背叛、恶行和权力之争。除了政治之争，书中也充满了奇幻元素。白步行者、龙、巨人、红女巫等等，都成为了书中令人难忘的角色和场景。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[Uopgpq1u]': {'id': '7df1dd54d2ffb1102ab7555a3a3026b70450bbcf41b605e9de07b628d5198ae4', 'description': '这些奇幻元素与现实世界的政治斗争融合在一起，使得整个故事更为生动有趣。除此之外，这本书中的角色也非常有特点。他们的性格、行为、语言都被塑造得十分立体鲜明，使得读者能够深入了解他们的内心世界。比如说提利昂·兰尼斯特，他是一个残忍却又聪明绝顶的角色，他用自己的智慧和手段掌控着家族的命运；琼恩·雪诺则是一个勇敢坚定、忠诚正直的角色，他在北方的长城上捍卫着王国的安全，面对的却是各种挑战和困难。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[CPUavslR]': {'id': 'd612db101a0dcecc3ee324cd09f31c883d5ce8b3f8506a995e36820ae46027a6', 'description': '¥15现货冰与火之歌全套平装15册1徽章淘宝旗舰店¥385.31¥664.2购买总之，《冰与火之歌》是一部令人着迷的作品，它融合了许多元素，以独特的方式呈现出一个充满人性、荣誉、背叛和权力之争的世界。作者乔治·R·R·马丁以他丰富的想象力和精湛的笔触，打造了一个宏大而又残酷的奇幻世界，让读者沉浸其中、忘却现实。如果你追求一个让你情感深刻、震撼人心的故事，那么《冰与火之歌》是一个非常好的选择。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[6uN8Ofsf]': {'id': '3a3c2e1c364d5c5de82e4847f7e2482db66086be31c00e6a19a26eb990427dc1', 'description': '新客立减 登录 冰与火之歌奇幻文学的经典之作 《冰与火之歌:奇幻文学的经典之作》 《冰与火之歌》是美国作家乔治 · R· R· 马丁创作的一部奇幻文学巨著,被誉为现代奇幻文学的经典之作。小说通过扑朔迷离的情节、复杂细 腻的人物关系、宏大壮阔的世界观,展现出了一个瑰丽而残酷的中世 纪式幻想世界。', 'title': '冰与火之歌奇幻文学的经典之作 - 百度文库', 'url': 'https://wenku.baidu.com/view/509323cae75c3b3567ec102de2bd960591c6d92c.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[vjP3Zc0O]': {'id': 'ef21cadf0552dfe34ca737d3624e0512f6fb910fea2bb61244c8fda81c5f54c3', 'description': '冰与火之歌系列共包括《权力的游戏》、《列王的纷争》、《冰雨 的风暴》、《群鸦的盛宴》、《魔龙的狂舞》以及尚未出版的两部续 作。该系列小说出版以来,在全球范围内掀起了一股奇幻文学热潮,被翻译成多种语言,并改编成成功的电视剧《权力的游戏》。《冰与火之歌》以细腻入微的人物刻画和复杂的家族关系网络为特 点。', 'title': '冰与火之歌奇幻文学的经典之作 - 百度文库', 'url': 'https://wenku.baidu.com/view/509323cae75c3b3567ec102de2bd960591c6d92c.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[bxnKfwkq]': {'id': 'aaee183300cd270bea7a6bc151bf699ebc0f55d18b7e5eeda408060595f7ca63', 'description': '冰与火之歌:权谋、荣耀与欲望的恢弘史诗 介绍 《冰与火之歌》是美国作家乔治·R·R·马丁创作的一部史诗奇幻小说系列,被广 泛誉为现代奇幻文学的巅峰之作。该系列小说以中世纪欧洲为背景,具有浓厚 的政治阴谋、荣耀和欲望的元素,引发了全球读者群体的狂热追捧。故事背景 故事发生在虚构的七大王国大陆上。数个封建领主家族和一个暴君共同统治这 片土地。', 'title': '《冰与火之歌》:权谋、荣耀与欲望的恢弘史诗 - 百度文库', 'url': 'https://wenku.baidu.com/view/45133a45d6bbfd0a79563c1ec5da50e2534dd10d.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[zy78I8QC]': {'id': '949bc6cf1f089fa628c07c435e2901f7d1de5eb46b7a4b59e8d83f2431e3ac21', 'description': '3.龙母:作为流亡贵族的最后一名幸存者,她带领三条幼龙逐渐成长,并向 铁王座发起挑战。她是荣耀与欲望的象征之一。情节剧变和复杂关系 1.纷争与叛乱:各个家族、各种势力之间展开了相互争斗、背叛和内讧的故 事情节。读者将跟随主人公们经历暗黑而曲折的命运。', 'title': '《冰与火之歌》:权谋、荣耀与欲望的恢弘史诗 - 百度文库', 'url': 'https://wenku.baidu.com/view/45133a45d6bbfd0a79563c1ec5da50e2534dd10d.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}}, 'use_for_check_items_content_dic': {'他亲口承认了包括玫瑰战争在内的诸多历史事件影响了他的写作过程,并最终反映到了小说之中,但是他亦坚持道:“书中并没有严格意义上的一对一关系,我更喜欢把历史当成一种调剂品,使得奇幻小说变得更加真实可靠,但绝不会简单地换个名字就挪到我的作品里面。”《冰与火之歌》中的多条情节线索和人物设定都与历史上的“玫瑰战争”相暗合,小说的两个主要家族:史塔克与兰尼斯特,分别代表了历史上的约克家族与兰开斯特家族。': '[YzbNJ0Qg]', '美剧 《冰与火之歌》 主要描述了在一片虚构的中世纪世界里所发生的一系列宫廷斗争、疆场厮杀、游历冒险和魔法抗衡的故事。《冰与火之歌》的故事发生在一个虚幻的中世纪世界,主要目光集中在西方的“日落王国”维斯特洛大陆 上,讲述那里的人在当时的政治背景下的遭遇和经历。第一条主线围绕着各方诸侯意图问鼎整个王国的权力中心 铁王座 而进行“权力的游戏”王朝斗争的故事展开。': '[9EeAZjyr]', '扩展资料 《权力的游戏》,是美国 HBO电视网 制作推出的一部中世纪史诗奇幻题材的电视剧。该剧改编自美国作家 乔治·R·R·马丁 的奇幻小说《冰与火之歌》系列。《权力的游戏》以“创造奇迹”的高姿态打破了魔幻剧难以取得成功的美剧“魔咒”,一举颠覆所有好莱坞魔幻电影的创意水平。': '[lBpKtwrS]', '它给予演员、导演、编剧创意的无限可能,以其无限且有序的创作空间囊括了成千上万形象饱满的人物角色、怪诞独特充满想象的风土人情,其空间之完整、细节之丰富、叙事之恣意让人感叹。《冰与火之歌》是由美国作家乔治·R·R·马丁所著的严肃奇幻小说系列。该书系列首卷于1996年初由矮脚鸡图书公司在美国出版,全书计划共七卷,截至2014年共完成出版了五卷,被译为三十多种文字。': '[KZICqZGs]', '乔治·R.R·马丁  如果你是《权力的游戏》或者原著《冰与火之歌》的粉丝，一定听说了作者乔治·R.R·马丁史诗般的新作《火与血》出版了。《火与血》讲述了《权利的游戏》里坦格利安家族的历史，是此系列的第一卷。虽然在2013年的时候，马丁曾计划等这一系列全部完成后再出版，但后来还是决定先出个两卷本。': '[2mMEVLs7]', '《火与血》英文版《冰与火之歌》改变的《权力的游戏》自2011年4月17日在美国HBO电视台首次播出以来，迎来连续多年的收视狂潮，在全世界赢得了无数忠实粉丝，2015年第67届艾美奖中破纪录地斩获12项大奖之后，今年又获得2018年第70届艾美奖最佳剧集奖。将于2019年4月播出的该系列第八季让很多人翘首以盼。如今《火与血》的出版，我们是不是又可以期待新作品的中文版引进，以及电视剧改编了呢？': '[OVyT4zTx]', '《火与血》描写的是《权游》中维斯特洛大陆的故事300年之前的事情。尽管差了几个世纪，然而根据最近马丁接受《娱乐周刊》（Entertainment Weekly）的采访来看，《火与血》中埋了一些关于《冰与火之歌》的小暗示。”确实有一些重要的小线索，不过我不会透露太多，读者必须自己去找出它们，然后辨别那些到底真的是暗示还是不过为了转移注意力的把戏。“马丁这样说。': '[x8T0Ogqg]', '我必须写完才行。“你都这么可爱地自责了，我们当然不会催你啦。马丁说《火与血》这本书对他来说是个很大的安慰，因为坦格利安家族系列完全是自己写出来的。很多人可能不太了解，此前的《冰与火之歌》是马丁和另一个作者伊莱奥·M·加西亚 Jr.合作写出，而这将是完全属于马丁自己的作品，是不是很期待呢？': '[qzY1q7J4]', '新客立减 登录 《冰与火之歌》主要情节 《冰与火之歌》是一部由美国作家乔治 · R· R· 马丁创作的史诗奇 幻小说系列,共有五卷。本书以中世纪为背景,讲述了七个王国 之间的权力斗争、家族恩怨以及古老的神秘力量的觉醒。以下是 《冰与火之歌》主要情节的梗概。第一卷:《权力的游戏》 本卷主要围绕斯塔克家族展开。史塔克家族是北境的贵族家族,由埃德 · 史塔克领导。': '[C3c2k1s0]', '在这个充满快餐文化的时代，我们渴望着一些能够让我们陶冶情操、感受深刻的故事。而《冰与火之歌》（冰与火之歌）这本作品无疑是能够满足我们这种需求的经典之作。这本书集奇幻、政治、战争、爱情、背叛等元素于一身，讲述了一个虚构的中世纪欧洲风格的世界，探讨了人性、道德和权力的主题，给我们带来了一个充满惊喜和震撼的阅读体验。': '[cvbxsXlw]', '在这个世界里，冰雪覆盖的北境、温暖宜人的南方、狂风肆虐的铁群岛、险峻的狭海、神秘的东方大陆等等，都成为了故事的背景。而书中许多角色也成为了经典，包括奈德·史塔克、提利昂·兰尼斯特、琼恩·雪诺、丹妮莉丝·坦格利安等等。他们的经历被交织在一起，构成了一个庞大而精致的史诗。《冰与火之歌》的故事情节复杂而精彩，这也是其最为吸引人的地方之一。在这个世界里，人人都有自己的目的和野心，都在为争夺铁王座而努力。': '[aJLxh2CK]', '身为诸侯之一的奈德·史塔克，却在一场与势力更大的家族兰尼斯特的斗争中意外地失去了自己的生命。他的儿子罗柏成为了北方的领袖，并承诺要为他的父亲复仇。同时，南方的兰尼斯特家族也在为掌握铁王座而斗争，不惜手段地谋杀敌对家族的成员，包括国王。整个故事的发展都充满着政治斗争、背叛、恶行和权力之争。除了政治之争，书中也充满了奇幻元素。白步行者、龙、巨人、红女巫等等，都成为了书中令人难忘的角色和场景。': '[CErsrEqh]', '这些奇幻元素与现实世界的政治斗争融合在一起，使得整个故事更为生动有趣。除此之外，这本书中的角色也非常有特点。他们的性格、行为、语言都被塑造得十分立体鲜明，使得读者能够深入了解他们的内心世界。比如说提利昂·兰尼斯特，他是一个残忍却又聪明绝顶的角色，他用自己的智慧和手段掌控着家族的命运；琼恩·雪诺则是一个勇敢坚定、忠诚正直的角色，他在北方的长城上捍卫着王国的安全，面对的却是各种挑战和困难。': '[Uopgpq1u]', '¥15现货冰与火之歌全套平装15册1徽章淘宝旗舰店¥385.31¥664.2购买总之，《冰与火之歌》是一部令人着迷的作品，它融合了许多元素，以独特的方式呈现出一个充满人性、荣誉、背叛和权力之争的世界。作者乔治·R·R·马丁以他丰富的想象力和精湛的笔触，打造了一个宏大而又残酷的奇幻世界，让读者沉浸其中、忘却现实。如果你追求一个让你情感深刻、震撼人心的故事，那么《冰与火之歌》是一个非常好的选择。': '[CPUavslR]', '新客立减 登录 冰与火之歌奇幻文学的经典之作 《冰与火之歌:奇幻文学的经典之作》 《冰与火之歌》是美国作家乔治 · R· R· 马丁创作的一部奇幻文学巨著,被誉为现代奇幻文学的经典之作。小说通过扑朔迷离的情节、复杂细 腻的人物关系、宏大壮阔的世界观,展现出了一个瑰丽而残酷的中世 纪式幻想世界。': '[6uN8Ofsf]', '冰与火之歌系列共包括《权力的游戏》、《列王的纷争》、《冰雨 的风暴》、《群鸦的盛宴》、《魔龙的狂舞》以及尚未出版的两部续 作。该系列小说出版以来,在全球范围内掀起了一股奇幻文学热潮,被翻译成多种语言,并改编成成功的电视剧《权力的游戏》。《冰与火之歌》以细腻入微的人物刻画和复杂的家族关系网络为特 点。': '[vjP3Zc0O]', '冰与火之歌:权谋、荣耀与欲望的恢弘史诗 介绍 《冰与火之歌》是美国作家乔治·R·R·马丁创作的一部史诗奇幻小说系列,被广 泛誉为现代奇幻文学的巅峰之作。该系列小说以中世纪欧洲为背景,具有浓厚 的政治阴谋、荣耀和欲望的元素,引发了全球读者群体的狂热追捧。故事背景 故事发生在虚构的七大王国大陆上。数个封建领主家族和一个暴君共同统治这 片土地。': '[bxnKfwkq]', '3.龙母:作为流亡贵族的最后一名幸存者,她带领三条幼龙逐渐成长,并向 铁王座发起挑战。她是荣耀与欲望的象征之一。情节剧变和复杂关系 1.纷争与叛乱:各个家族、各种势力之间展开了相互争斗、背叛和内讧的故 事情节。读者将跟随主人公们经历暗黑而曲折的命运。': '[zy78I8QC]'}, 'use_for_check_items_opinion_similarity_dic': {'他亲口承认了包括玫瑰战争在内的诸多历史事件影响了他的写作过程,并最终反映到了小说之中,但是他亦坚持道:“书中并没有严格意义上的一对一关系,我更喜欢把历史当成一种调剂品,使得奇幻小说变得更加真实可靠,但绝不会简单地换个名字就挪到我的作品里面。”《冰与火之歌》中的多条情节线索和人物设定都与历史上的“玫瑰战争”相暗合,小说的两个主要家族:史塔克与兰尼斯特,分别代表了历史上的约克家族与兰开斯特家族。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5830847024917603, '冰与火之歌小说系列的故事主线是什么？': 0.5805013179779053, '冰与火之歌小说系列的主要事件是什么？': 0.571262001991272, '冰与火之歌小说系列的故事背景是什么？': 0.5941958427429199, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5606472492218018, '冰与火之歌小说系列的主题是什么？': 0.546190083026886, '冰与火之歌小说系列的成功因素有哪些？': 0.5448422431945801, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5118087530136108, '乔治·R·R·马丁是谁？': 0.25151216983795166}, '美剧 《冰与火之歌》 主要描述了在一片虚构的中世纪世界里所发生的一系列宫廷斗争、疆场厮杀、游历冒险和魔法抗衡的故事。《冰与火之歌》的故事发生在一个虚幻的中世纪世界,主要目光集中在西方的“日落王国”维斯特洛大陆 上,讲述那里的人在当时的政治背景下的遭遇和经历。第一条主线围绕着各方诸侯意图问鼎整个王国的权力中心 铁王座 而进行“权力的游戏”王朝斗争的故事展开。': {'冰与火之歌小说系列的主要人物有哪些？': 0.522656261920929, '冰与火之歌小说系列的故事主线是什么？': 0.5978350043296814, '冰与火之歌小说系列的主要事件是什么？': 0.5671646595001221, '冰与火之歌小说系列的故事背景是什么？': 0.5610002279281616, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5271753072738647, '冰与火之歌小说系列的主题是什么？': 0.5246851444244385, '冰与火之歌小说系列的成功因素有哪些？': 0.5023845434188843, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4330064356327057, '乔治·R·R·马丁是谁？': 0.18719661235809326}, '扩展资料 《权力的游戏》,是美国 HBO电视网 制作推出的一部中世纪史诗奇幻题材的电视剧。该剧改编自美国作家 乔治·R·R·马丁 的奇幻小说《冰与火之歌》系列。《权力的游戏》以“创造奇迹”的高姿态打破了魔幻剧难以取得成功的美剧“魔咒”,一举颠覆所有好莱坞魔幻电影的创意水平。': {'冰与火之歌小说系列的主要人物有哪些？': 0.47262707352638245, '冰与火之歌小说系列的故事主线是什么？': 0.49120235443115234, '冰与火之歌小说系列的主要事件是什么？': 0.5062974691390991, '冰与火之歌小说系列的故事背景是什么？': 0.5224155187606812, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.4569784700870514, '冰与火之歌小说系列的主题是什么？': 0.4918754994869232, '冰与火之歌小说系列的成功因素有哪些？': 0.4785429835319519, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.41328859329223633, '乔治·R·R·马丁是谁？': 0.3317170739173889}, '它给予演员、导演、编剧创意的无限可能,以其无限且有序的创作空间囊括了成千上万形象饱满的人物角色、怪诞独特充满想象的风土人情,其空间之完整、细节之丰富、叙事之恣意让人感叹。《冰与火之歌》是由美国作家乔治·R·R·马丁所著的严肃奇幻小说系列。该书系列首卷于1996年初由矮脚鸡图书公司在美国出版,全书计划共七卷,截至2014年共完成出版了五卷,被译为三十多种文字。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5424028038978577, '冰与火之歌小说系列的故事主线是什么？': 0.5208942890167236, '冰与火之歌小说系列的主要事件是什么？': 0.530415952205658, '冰与火之歌小说系列的故事背景是什么？': 0.5498812198638916, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.48795801401138306, '冰与火之歌小说系列的主题是什么？': 0.5245355367660522, '冰与火之歌小说系列的成功因素有哪些？': 0.5352681279182434, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5294638276100159, '乔治·R·R·马丁是谁？': 0.3067325949668884}, '乔治·R.R·马丁  如果你是《权力的游戏》或者原著《冰与火之歌》的粉丝，一定听说了作者乔治·R.R·马丁史诗般的新作《火与血》出版了。《火与血》讲述了《权利的游戏》里坦格利安家族的历史，是此系列的第一卷。虽然在2013年的时候，马丁曾计划等这一系列全部完成后再出版，但后来还是决定先出个两卷本。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5470727682113647, '冰与火之歌小说系列的故事主线是什么？': 0.5303211212158203, '冰与火之歌小说系列的主要事件是什么？': 0.5636633634567261, '冰与火之歌小说系列的故事背景是什么？': 0.559965193271637, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.4808250665664673, '冰与火之歌小说系列的主题是什么？': 0.5303019285202026, '冰与火之歌小说系列的成功因素有哪些？': 0.5003072619438171, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4798562824726105, '乔治·R·R·马丁是谁？': 0.571890652179718}, '《火与血》英文版《冰与火之歌》改变的《权力的游戏》自2011年4月17日在美国HBO电视台首次播出以来，迎来连续多年的收视狂潮，在全世界赢得了无数忠实粉丝，2015年第67届艾美奖中破纪录地斩获12项大奖之后，今年又获得2018年第70届艾美奖最佳剧集奖。将于2019年4月播出的该系列第八季让很多人翘首以盼。如今《火与血》的出版，我们是不是又可以期待新作品的中文版引进，以及电视剧改编了呢？': {'冰与火之歌小说系列的主要人物有哪些？': 0.49481016397476196, '冰与火之歌小说系列的故事主线是什么？': 0.4986376166343689, '冰与火之歌小说系列的主要事件是什么？': 0.5366332530975342, '冰与火之歌小说系列的故事背景是什么？': 0.5315499305725098, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5149340033531189, '冰与火之歌小说系列的主题是什么？': 0.5138964056968689, '冰与火之歌小说系列的成功因素有哪些？': 0.5063655972480774, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4651692807674408, '乔治·R·R·马丁是谁？': 0.30041244626045227}, '《火与血》描写的是《权游》中维斯特洛大陆的故事300年之前的事情。尽管差了几个世纪，然而根据最近马丁接受《娱乐周刊》（Entertainment Weekly）的采访来看，《火与血》中埋了一些关于《冰与火之歌》的小暗示。”确实有一些重要的小线索，不过我不会透露太多，读者必须自己去找出它们，然后辨别那些到底真的是暗示还是不过为了转移注意力的把戏。“马丁这样说。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5312796235084534, '冰与火之歌小说系列的故事主线是什么？': 0.607370138168335, '冰与火之歌小说系列的主要事件是什么？': 0.590825080871582, '冰与火之歌小说系列的故事背景是什么？': 0.6291518211364746, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5607295632362366, '冰与火之歌小说系列的主题是什么？': 0.5580481886863708, '冰与火之歌小说系列的成功因素有哪些？': 0.5445112586021423, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5173963308334351, '乔治·R·R·马丁是谁？': 0.34022295475006104}, '我必须写完才行。“你都这么可爱地自责了，我们当然不会催你啦。马丁说《火与血》这本书对他来说是个很大的安慰，因为坦格利安家族系列完全是自己写出来的。很多人可能不太了解，此前的《冰与火之歌》是马丁和另一个作者伊莱奥·M·加西亚 Jr.合作写出，而这将是完全属于马丁自己的作品，是不是很期待呢？': {'冰与火之歌小说系列的主要人物有哪些？': 0.5334891676902771, '冰与火之歌小说系列的故事主线是什么？': 0.5522834062576294, '冰与火之歌小说系列的主要事件是什么？': 0.5461595058441162, '冰与火之歌小说系列的故事背景是什么？': 0.5646006464958191, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5037646889686584, '冰与火之歌小说系列的主题是什么？': 0.5503731966018677, '冰与火之歌小说系列的成功因素有哪些？': 0.5187556743621826, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4974684715270996, '乔治·R·R·马丁是谁？': 0.4253619313240051}, '新客立减 登录 《冰与火之歌》主要情节 《冰与火之歌》是一部由美国作家乔治 · R· R· 马丁创作的史诗奇 幻小说系列,共有五卷。本书以中世纪为背景,讲述了七个王国 之间的权力斗争、家族恩怨以及古老的神秘力量的觉醒。以下是 《冰与火之歌》主要情节的梗概。第一卷:《权力的游戏》 本卷主要围绕斯塔克家族展开。史塔克家族是北境的贵族家族,由埃德 · 史塔克领导。': {'冰与火之歌小说系列的主要人物有哪些？': 0.6290047764778137, '冰与火之歌小说系列的故事主线是什么？': 0.6474533081054688, '冰与火之歌小说系列的主要事件是什么？': 0.6427901387214661, '冰与火之歌小说系列的故事背景是什么？': 0.6317615509033203, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.6134090423583984, '冰与火之歌小说系列的主题是什么？': 0.6010677814483643, '冰与火之歌小说系列的成功因素有哪些？': 0.5466427206993103, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.48217761516571045, '乔治·R·R·马丁是谁？': 0.25230029225349426}, '在这个充满快餐文化的时代，我们渴望着一些能够让我们陶冶情操、感受深刻的故事。而《冰与火之歌》（冰与火之歌）这本作品无疑是能够满足我们这种需求的经典之作。这本书集奇幻、政治、战争、爱情、背叛等元素于一身，讲述了一个虚构的中世纪欧洲风格的世界，探讨了人性、道德和权力的主题，给我们带来了一个充满惊喜和震撼的阅读体验。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5589199662208557, '冰与火之歌小说系列的故事主线是什么？': 0.6032648086547852, '冰与火之歌小说系列的主要事件是什么？': 0.5889384746551514, '冰与火之歌小说系列的故事背景是什么？': 0.6350045800209045, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5445408225059509, '冰与火之歌小说系列的主题是什么？': 0.603825569152832, '冰与火之歌小说系列的成功因素有哪些？': 0.5973975658416748, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.567415714263916, '乔治·R·R·马丁是谁？': 0.2542561888694763}, '在这个世界里，冰雪覆盖的北境、温暖宜人的南方、狂风肆虐的铁群岛、险峻的狭海、神秘的东方大陆等等，都成为了故事的背景。而书中许多角色也成为了经典，包括奈德·史塔克、提利昂·兰尼斯特、琼恩·雪诺、丹妮莉丝·坦格利安等等。他们的经历被交织在一起，构成了一个庞大而精致的史诗。《冰与火之歌》的故事情节复杂而精彩，这也是其最为吸引人的地方之一。在这个世界里，人人都有自己的目的和野心，都在为争夺铁王座而努力。': {'冰与火之歌小说系列的主要人物有哪些？': 0.6508440971374512, '冰与火之歌小说系列的故事主线是什么？': 0.654075026512146, '冰与火之歌小说系列的主要事件是什么？': 0.6263918876647949, '冰与火之歌小说系列的故事背景是什么？': 0.6792794466018677, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.6192997694015503, '冰与火之歌小说系列的主题是什么？': 0.617631196975708, '冰与火之歌小说系列的成功因素有哪些？': 0.6464900970458984, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5506643056869507, '乔治·R·R·马丁是谁？': 0.2508317232131958}, '身为诸侯之一的奈德·史塔克，却在一场与势力更大的家族兰尼斯特的斗争中意外地失去了自己的生命。他的儿子罗柏成为了北方的领袖，并承诺要为他的父亲复仇。同时，南方的兰尼斯特家族也在为掌握铁王座而斗争，不惜手段地谋杀敌对家族的成员，包括国王。整个故事的发展都充满着政治斗争、背叛、恶行和权力之争。除了政治之争，书中也充满了奇幻元素。白步行者、龙、巨人、红女巫等等，都成为了书中令人难忘的角色和场景。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5198290348052979, '冰与火之歌小说系列的故事主线是什么？': 0.49745866656303406, '冰与火之歌小说系列的主要事件是什么？': 0.5428277254104614, '冰与火之歌小说系列的故事背景是什么？': 0.5097785592079163, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5069944858551025, '冰与火之歌小说系列的主题是什么？': 0.48197710514068604, '冰与火之歌小说系列的成功因素有哪些？': 0.4867812395095825, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4208918809890747, '乔治·R·R·马丁是谁？': 0.2670937478542328}, '这些奇幻元素与现实世界的政治斗争融合在一起，使得整个故事更为生动有趣。除此之外，这本书中的角色也非常有特点。他们的性格、行为、语言都被塑造得十分立体鲜明，使得读者能够深入了解他们的内心世界。比如说提利昂·兰尼斯特，他是一个残忍却又聪明绝顶的角色，他用自己的智慧和手段掌控着家族的命运；琼恩·雪诺则是一个勇敢坚定、忠诚正直的角色，他在北方的长城上捍卫着王国的安全，面对的却是各种挑战和困难。': {'冰与火之歌小说系列的主要人物有哪些？': 0.45925062894821167, '冰与火之歌小说系列的故事主线是什么？': 0.45566484332084656, '冰与火之歌小说系列的主要事件是什么？': 0.44420769810676575, '冰与火之歌小说系列的故事背景是什么？': 0.4719628691673279, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.44721806049346924, '冰与火之歌小说系列的主题是什么？': 0.44245555996894836, '冰与火之歌小说系列的成功因素有哪些？': 0.5321061611175537, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4622625410556793, '乔治·R·R·马丁是谁？': 0.27265214920043945}, '¥15现货冰与火之歌全套平装15册1徽章淘宝旗舰店¥385.31¥664.2购买总之，《冰与火之歌》是一部令人着迷的作品，它融合了许多元素，以独特的方式呈现出一个充满人性、荣誉、背叛和权力之争的世界。作者乔治·R·R·马丁以他丰富的想象力和精湛的笔触，打造了一个宏大而又残酷的奇幻世界，让读者沉浸其中、忘却现实。如果你追求一个让你情感深刻、震撼人心的故事，那么《冰与火之歌》是一个非常好的选择。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5492427349090576, '冰与火之歌小说系列的故事主线是什么？': 0.5673253536224365, '冰与火之歌小说系列的主要事件是什么？': 0.566727876663208, '冰与火之歌小说系列的故事背景是什么？': 0.5986763834953308, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5307523608207703, '冰与火之歌小说系列的主题是什么？': 0.5659594535827637, '冰与火之歌小说系列的成功因素有哪些？': 0.5745295286178589, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5596000552177429, '乔治·R·R·马丁是谁？': 0.4660329520702362}, '新客立减 登录 冰与火之歌奇幻文学的经典之作 《冰与火之歌:奇幻文学的经典之作》 《冰与火之歌》是美国作家乔治 · R· R· 马丁创作的一部奇幻文学巨著,被誉为现代奇幻文学的经典之作。小说通过扑朔迷离的情节、复杂细 腻的人物关系、宏大壮阔的世界观,展现出了一个瑰丽而残酷的中世 纪式幻想世界。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5250936150550842, '冰与火之歌小说系列的故事主线是什么？': 0.5156024098396301, '冰与火之歌小说系列的主要事件是什么？': 0.5273780822753906, '冰与火之歌小说系列的故事背景是什么？': 0.5429602861404419, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5077226758003235, '冰与火之歌小说系列的主题是什么？': 0.515972375869751, '冰与火之歌小说系列的成功因素有哪些？': 0.5131537914276123, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5270513296127319, '乔治·R·R·马丁是谁？': 0.2713403105735779}, '冰与火之歌系列共包括《权力的游戏》、《列王的纷争》、《冰雨 的风暴》、《群鸦的盛宴》、《魔龙的狂舞》以及尚未出版的两部续 作。该系列小说出版以来,在全球范围内掀起了一股奇幻文学热潮,被翻译成多种语言,并改编成成功的电视剧《权力的游戏》。《冰与火之歌》以细腻入微的人物刻画和复杂的家族关系网络为特 点。': {'冰与火之歌小说系列的主要人物有哪些？': 0.6072996854782104, '冰与火之歌小说系列的故事主线是什么？': 0.5810346007347107, '冰与火之歌小说系列的主要事件是什么？': 0.6145420074462891, '冰与火之歌小说系列的故事背景是什么？': 0.6060986518859863, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5557041764259338, '冰与火之歌小说系列的主题是什么？': 0.5955089330673218, '冰与火之歌小说系列的成功因素有哪些？': 0.5777203440666199, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5498838424682617, '乔治·R·R·马丁是谁？': 0.23272541165351868}, '冰与火之歌:权谋、荣耀与欲望的恢弘史诗 介绍 《冰与火之歌》是美国作家乔治·R·R·马丁创作的一部史诗奇幻小说系列,被广 泛誉为现代奇幻文学的巅峰之作。该系列小说以中世纪欧洲为背景,具有浓厚 的政治阴谋、荣耀和欲望的元素,引发了全球读者群体的狂热追捧。故事背景 故事发生在虚构的七大王国大陆上。数个封建领主家族和一个暴君共同统治这 片土地。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5277740359306335, '冰与火之歌小说系列的故事主线是什么？': 0.5353829860687256, '冰与火之歌小说系列的主要事件是什么？': 0.5342440605163574, '冰与火之歌小说系列的故事背景是什么？': 0.5584322214126587, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.48513564467430115, '冰与火之歌小说系列的主题是什么？': 0.522860586643219, '冰与火之歌小说系列的成功因素有哪些？': 0.510589599609375, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.47407639026641846, '乔治·R·R·马丁是谁？': 0.2640494108200073}, '3.龙母:作为流亡贵族的最后一名幸存者,她带领三条幼龙逐渐成长,并向 铁王座发起挑战。她是荣耀与欲望的象征之一。情节剧变和复杂关系 1.纷争与叛乱:各个家族、各种势力之间展开了相互争斗、背叛和内讧的故 事情节。读者将跟随主人公们经历暗黑而曲折的命运。': {'冰与火之歌小说系列的主要人物有哪些？': 0.477159708738327, '冰与火之歌小说系列的故事主线是什么？': 0.48683562874794006, '冰与火之歌小说系列的主要事件是什么？': 0.5140298008918762, '冰与火之歌小说系列的故事背景是什么？': 0.479809045791626, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5342103838920593, '冰与火之歌小说系列的主题是什么？': 0.45075446367263794, '冰与火之歌小说系列的成功因素有哪些？': 0.47802644968032837, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.37755483388900757, '乔治·R·R·马丁是谁？': 0.2073982059955597}}})

    encoded = context_encode(contextaaaaa)
    save_to_es(encoded, 987987)

    data = load_from_es({
        "query": {
            "bool": {
                "must": [
                    {"match": {"session_id": 987987}}
                ]
            }
        },
        "size": 10  # Limit the number of returned documents to 1000
    }, es_name="ES_QA", index_name="default")
    decoded_context = context_decode(data)

    user_id = contextaaaaa.get_user_id()
    print(user_id)