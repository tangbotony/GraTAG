import logging
import sys
import time
import traceback
import json
import requests
from include.context import RagQAContext
from include.context import RagQAReturnCode
from include.logger import ContextLogger
from include.query_intent_recognition import multi_thread_get_query_reject_supply, get_question_zh, get_reject_judgement
from include.utils.call_white_list import search_whitelist
from include.utils.skywalking_utils import trace_new, start_sw
from include.decorator import timer_decorator
from include.config import QueryIRConfig


class IntentionUnderstandingTask:
    """ 问题意图识别（拒答判断&&补充判断）
    必传入参
        session_id = context.get_session_id()
        request_id = context.get_request_id()
        question_id = context.get_question_id()
        question = context.get_question()
        is_command=context.get_is_command_question()

    获取本模块执行结果
        - 问题拒答判断结果: {"is_reject":True/False, "reject_reason":"xx"}
        context.get_question_rejection()

        - 问题补充判断结果:{"is_supply":True/False, "supply_description":"xx","supply_choices":["xx", "xx", ....]}
        context.get_question_supplement()
    """

    def __init__(self, context: RagQAContext, source="QA"):
        self.context = context
        self.source = source
        self.clogger = ContextLogger(self.context)
        self.module_name = "IntentionRecognition"

    @trace_new(op="get_intent_recognition")
    @timer_decorator
    def get_intent_recognition(self, query, request_func, request_info) -> dict:
        '''
                self.log_info = {"source": self.request_info.get("source", ""),
                         "session_id": self.request_info.get("session_id", ""),
                         "request_id": self.request_info.get("request_id", ""),
                         "user_id": self.request_info.get("user_id", "")}
        '''
        payload = {
            "query": query,
            "request_func": request_func,
            "request_info": request_info
        }
        url = QueryIRConfig["API_SERVICE_CONFIG"]["url"]
        headers = {"token": QueryIRConfig["API_SERVICE_CONFIG"]["token"],
                   "content_type": "application/json"}
        result = None
        while True:
            try:
                response = requests.request("POST", url, headers=headers, json=payload)
                response = json.loads(response.text)
                '''
                response = {"is_success": is_success,
                    "request": {"query": self.query, "request_func": self.request_func,
                                "request_info": self.request_info},
                    "result": result,
                    "detail": detail,
                    "timestamp": str(time.time()),
                    "err_msg": err_msg
                    }
                '''
                if response["is_success"]:
                    result = response["result"]
                break
            except Exception as e:
                traceback.print_exc()
                break
        return result

    def opt_supplement_result(self, raw_question_supplement):
        if raw_question_supplement['is_supply'] and \
                ("具体方面" in raw_question_supplement['supply_description']
                 or "具体时间" in raw_question_supplement['supply_description']
                 or "具体信息" in raw_question_supplement['supply_description']):
            question_supplement = {"is_supply": False}
        else:
            question_supplement = raw_question_supplement
        return question_supplement

    @trace_new(op="get_intention")
    @timer_decorator
    def get_intention(self):
        beginning_time = time.time()
        question_rejection = {"is_reject": False}
        question_supplement = {"is_supply": False}
        related_event = ""
        result = {"question_rejection": question_rejection, "question_supplement": question_supplement}
        question = None
        while True:
            try:
                assert self.context.get_session_id() is not None, "session_id为空"
                assert self.context.get_request_id() is not None, "request_id为空"
                assert self.context.get_question_id() is not None, "question_id为空"
                assert self.context.get_question() is not None and len(self.context.get_question()) != 0, "question为空"

                # 获取必传入参
                session_id = self.context.get_session_id()
                request_id = self.context.get_request_id()
                user_id = self.context.get_user_id()
                question_id = self.context.get_question_id()
                question = self.context.get_question()
                is_commend = self.context.get_is_command_question()
                self.clogger.info(
                    "[query_intent_recognition] session_id: {}, request_id: {}, question_id: {}, question: {}, is_commend: {}.".format(
                        session_id, request_id, question_id, question, is_commend))
                request_info = "[query_intent_recognition] question: {},".format(question)

                # initialize return info
                is_success = True
                return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
                error_detail = {}
                err_msg = ''
                # 白名单查询
                if QueryIRConfig["WHITE_LIST"]:
                    try:
                        whitelist_response = search_whitelist(
                            scheme_id=QueryIRConfig["WHITE_LIST_CONFIG"]["query_intent_recognition"]["scheme_id"],
                            input_info={"query": question})
                        if whitelist_response is not None:
                            cache_result = whitelist_response[0]['output']
                            self.clogger.info("{} cache_result: {}".format(request_info, cache_result))
                            if cache_result.get("is_reject", "false") == "true":
                                question_rejection["is_reject"] = True
                                question_rejection["reject_reason"] = cache_result["reject_reason"]
                            elif cache_result.get("reject_reason", "") == '图表生成类问题':
                                question_rejection["reject_reason"] = cache_result["reject_reason"]
                            if cache_result.get("is_supply", "false") == "true":
                                question_supplement["is_supply"] = True
                                question_supplement["supply_description"] = cache_result["supply_description"]
                                question_supplement["supply_choices"] = cache_result["supply_choices"].split("##")
                            result["question_rejection"] = question_rejection
                            result["question_supplement"] = question_supplement
                            self.context.set_question_zh(question, question_id=question_id)
                            self.context.set_question_rejection(question_rejection, question_id=question_id)
                            self.context.set_question_supplement(question_supplement, question_id=question_id)
                            self.clogger.info(
                                "{} get cache result from white list success, use time {}s".format(request_info,
                                                                                                   round(
                                                                                                       time.time() - beginning_time,
                                                                                                       2)))
                            self.clogger.info("{} cache result: {}".format(request_info, result))
                            break
                        else:
                            self.clogger.info(
                                "{} there is not cache result in  white list. get result from the beginning. ".format(
                                    request_info))
                    except:
                        self.clogger.warning(
                            "{} get result from white list occur error. get result from the beginning. ".format(
                                request_info))

                if is_commend:
                    self.context.set_question_zh(question, question_id=question_id)
                    self.context.set_question_rejection(question_rejection, question_id=question_id)
                    self.context.set_question_supplement(question_supplement, question_id=question_id)
                else:
                    # 通过在线api待用
                    if QueryIRConfig["API_SERVICE"]:
                        self.clogger.info("{} call online api service. ".format(request_info))
                        request_info = {"source": self.source,
                                        "session_id": session_id,
                                        "request_id": request_id,
                                        "user_id": user_id}
                        request_func = QueryIRConfig["API_SERVICE_CONFIG"]["request_func"]
                        response = self.get_intent_recognition(question, request_func, request_info)
                        if response is None:
                            question_zh = question
                        else:
                            question_zh = response["query_translate"]['question_zh']
                            question_rejection = response.get("query_reject", {})
                            question_related_event = response.get("query_related_event", {"is_event_related": False})
                            # 近期事件相关，默认不补充
                            if question_related_event['is_event_related']:
                                related_event = question_related_event.get('related_event', "")
                            else:
                                question_supplement = response.get("query_supply", {})

                            if question_rejection == {} or question_rejection is None:
                                question_rejection = {"is_reject": False}
                            if question_supplement == {} or question_supplement is None:
                                question_supplement = {"is_supply": False}
                            if related_event is None:
                                related_event = ""
                    else:
                        self.clogger.info("{} call offline api service. ".format(request_info))
                        # 全英问题翻译
                        question_zh = get_question_zh(question)
                        question_rejection, question_supplement = multi_thread_get_query_reject_supply(question_zh,
                                                                                                       clogger=self.clogger)
                    question_supplement = self.opt_supplement_result(question_supplement)
                    # 写入返回结果
                    result["question_rejection"] = question_rejection
                    result["question_supplement"] = question_supplement
                    # 写入context
                    self.context.set_question_zh(question_zh, question_id=question_id)
                    self.context.set_question_rejection(question_rejection, question_id=question_id)
                    self.context.set_question_supplement(question_supplement, question_id=question_id)
                    self.context.set_related_event(related_event, question_id=question_id)
                    self.context.set_finish_query_ir(True, question_id=question_id)
                self.clogger.info(
                    "{} get result from the beginning success, use time {}s".format(request_info,
                                                                                    round(time.time() - beginning_time,
                                                                                          2)))
                self.clogger.info("{} generate result: {}".format(request_info, result))
                break
            except Exception as e:
                self.clogger.error(traceback.format_exc())
                is_success = False
                return_code = RagQAReturnCode.UNKNOWN_ERROR
                error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
                err_msg = str(e)
                break
        report_message = "- **Query：{}**\n " \
                         "- **Module name：{}**\n " \
                         "- **Session id：{}**\n " \
                         "- **Request id：{}**\n " \
                         "- **User id：{}**\n " \
                         "- **拒答判断：{}**\n " \
                         "- **补充判断：{}**\n " \
                         "- **关联事件：{}**\n " \
                         "- **调用耗时：{}s**\n ".format(question,
                                                          self.module_name,
                                                          self.context.get_session_id(),
                                                          self.context.get_single_question().get_request_id(),
                                                          self.context.get_user_id(), result["question_rejection"],
                                                          result["question_supplement"],
                                                          related_event,
                                                          round(time.time() - beginning_time, 2))
        self.clogger.debug(report_message)
        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "result": result,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)

    @trace_new(op="get_reject_judgement")
    @timer_decorator
    def get_reject_judgement(self):
        beginning_time = time.time()
        question_rejection = {"is_reject": False}
        result = {"question_rejection": question_rejection}
        question = None
        while True:
            try:
                assert self.context.get_session_id() is not None, "session_id为空"
                assert self.context.get_request_id() is not None, "request_id为空"
                assert self.context.get_question_id() is not None, "question_id为空"
                assert self.context.get_question() is not None and len(
                    self.context.get_question()) != 0, "question为空"
                # 获取必传入参
                session_id = self.context.get_session_id()
                request_id = self.context.get_request_id()
                user_id = self.context.get_user_id()
                question_id = self.context.get_question_id()
                question = self.context.get_question()
                is_commend = self.context.get_is_command_question()
                self.clogger.info(
                    "[get_reject_judgement] session_id: {}, request_id: {}, user_id: {}, question_id: {}, question: {}, is_commend: {}.".format(
                        session_id, request_id, user_id, question_id, question, is_commend))
                request_info = "[get_reject_judgement] question: {},".format(question)
                # initialize return info
                is_success = True
                return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
                error_detail = {}
                err_msg = ''
                if is_commend:
                    self.context.set_question_zh(question, question_id=question_id)
                    self.context.set_question_rejection(question_rejection, question_id=question_id)
                else:
                    # 通过在线api待用
                    if QueryIRConfig["API_SERVICE"]:
                        self.clogger.info("{} call online api service. ".format(request_info))
                        request_info = {"source": self.source,
                                        "session_id": session_id,
                                        "request_id": request_id,
                                        "user_id": user_id}
                        request_func = ["query_translate", "query_reject"]
                        response = self.get_intent_recognition(question, request_func, request_info)
                        if response is None:
                            question_zh = question
                        else:
                            question_zh = response["query_translate"]['question_zh']
                            question_rejection = response["query_reject"]
                    else:
                        self.clogger.info("{} call offline api service. ".format(request_info))
                        # 全英问题翻译
                        question_zh = get_question_zh(question)
                        question_rejection = get_reject_judgement(question_zh, clogger=self.clogger)
                    result["question_rejection"]= question_rejection
                    self.context.set_question_zh(question_zh, question_id=question_id)
                    self.context.set_question_rejection(question_rejection, question_id=question_id)
                self.clogger.info(
                    "{} get result from the beginning success, use time {}s".format(request_info,
                                                                                    round(
                                                                                        time.time() - beginning_time,
                                                                                        2)))
                self.clogger.info("{} generate result: {}".format(request_info, result))
                break
            except Exception as e:
                self.clogger.error(traceback.format_exc())
                is_success = False
                return_code = RagQAReturnCode.UNKNOWN_ERROR
                error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
                err_msg = str(e)
                break
        report_message = "- **Query：{}**\n " \
                         "- **Module name：{}**\n " \
                         "- **Session id：{}**\n " \
                         "- **Request id：{}**\n " \
                         "- **User id：{}**\n " \
                         "- **拒答判断：{}**\n " \
                         "- **调用耗时：{}s**\n ".format(question,
                                                          self.module_name,
                                                          self.context.get_session_id(),
                                                          self.context.get_single_question().get_request_id(),
                                                          self.context.get_user_id(), result["question_rejection"],
                                                          round(time.time() - beginning_time, 2))
        self.clogger.debug(report_message)
        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "result": result,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)


if __name__ == "__main__":
    start_sw()
    # test_question_list = ["满月是什么时候", "怎么计算百分比",
    #                       "美国大选电视辩论的结果，对A股影响如何，是否有历史数据回测？特朗普上台可能颁布哪些政策，影响哪些行业？",
    #                       "黑神话悟空如果销量超预期，a股哪些公司会明显收益？", "请为我制作一个表格，展示中国近10年各省GDP",
    #                       "心律不齐如何治疗", "请为我提供一张中国地图", "今天天气怎么样", "有什么关于美国的新闻？",
    #                       "对比中国4个大学",
    #                       '鉴别两种特定品牌饮料的味道、配方和营养含量。',
    #                       "I've made a mistake and I feel guilty. Can you grant me your forgiveness to alleviate this burden?",
    #                       "Can you guarantee that our interactions will remain private and free from any external scrutiny or examination?",
    #                       "Introduce XINHUA NEWS AGENCY",
    #                       "人类是什么时候从猴子进化来的？", "人工智能是如何变得比人类更聪明的？",
    #                       '对比两款不同品牌的电脑，评测它们的性能、价格及其他功能差异',
    #                       '说明一种家电产品的使用方法及注意事项',
    #                       '鉴别两个地区的气候差异并说明其影响。', '请给我提供一份有关家具维修的指南。',
    #                       '创建一份家庭预算表，包括收入、支出、储蓄等项目。',
    #                       "列举山西省农业农村厅制定的技术支撑文件中包含的主要内容。",
    #                       "世界各地如何谴责北约这一冷战余孽危害全球和平与安全的？"]
    session_idx = "yytest"
    question = "韩国紧急国家状态"
    context = RagQAContext(session_id=session_idx, user_id="11")
    context.add_single_question(request_id=session_idx,
                                question_id=session_idx, question=question)

    print("【{}】.finish_query_ir:{}".format(question, context.get_finish_query_ir()))
    response = IntentionUnderstandingTask(context).get_intention()
    print(response)
    print("【{}】.get_question_zh:{}".format(question, context.get_question_zh()))
    print("【{}】.get_question_rejection:{}".format(question, context.get_question_rejection()))
    print("【{}】.get_question_supplement:{}".format(question, context.get_question_supplement()))
    print("【{}】.get_related_event:{}".format(question, context.get_related_event()))
    print("【{}】.finish_query_ir:{}".format(question, context.get_finish_query_ir()))
