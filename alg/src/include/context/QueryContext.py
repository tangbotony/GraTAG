import copy
import string
import pickle
import base64
# from include.utils.skywalking_utils import trace_new, record_thread

DEFAULT_JSON = {
    "character": [],
    "location": [],
    "keywords": [],
    "start_time": "",
    "end_time": ""
}


class QueryContext():
    # @trace_new()
    def __init__(self,
                 request_id):
        """
        创建一个context对象
        :param session_id: 会话ID
        :param request_id: 请求ID
        }
        """
        self._request_id = request_id  # request_id
        self._recommend_questions = [] #推荐的问题
        self._recommend_query = [] #query补全
        self._question = None
        self._return_all = False

    def get_request_id(self):
        return self._request_id
    
    def set_request_id(self, request_id):
        self._request_id = request_id
    
    def set_recommend_questions(self, recommend_questions):
        self._recommend_questions = recommend_questions

    # @trace_new()
    def get_recommend_questions(self):
        return self._recommend_questions

    def set_recommend_query(self, recommend_query):
        self._recommend_query = recommend_query

    def get_recommend_query(self):
        return self._recommend_query
    
    def get_question(self):
        return self._question
    
    def set_question(self, question):
        self._question = question

    def set_return(self, return_all):
        self._return_all = return_all

    def get_return(self):
        return self._return_all