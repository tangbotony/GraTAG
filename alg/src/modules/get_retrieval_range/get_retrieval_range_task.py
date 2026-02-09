import json
import time
import ast
import traceback
import datetime
from include.logger import log
from include.utils.llm_caller_utils import llm_call
from include.context import RagQAReturnCode, RagQAContext, context_encode, context_decode
import re
from include.config import PromptConfig, RagQAConfig
from include.decorator import timer_decorator

DEFAULT_JSON = {
    "character": [],
    "location": [],
    "keywords": [],
    "keyword_all":[],
    "start_time": "",
    "end_time": ""
}

DEFAULT_RES = json.dumps({
    "is_success": False,
    "return_code": RagQAReturnCode.UNKNOWN_ERROR,
    "result": DEFAULT_JSON,
    "timestamp": str(time.time()),
    "err_msg": str("")
}, ensure_ascii=False)




def convert_chinese_time_to_date(chinese_time):
    # 获取当前日期
    now = datetime.datetime.now()

    if chinese_time == "今年":
        # 返回今年的第一天
        return f"{now.year}-01-01",0
    elif chinese_time == "今天":
        # 返回今天的日期
        return now.strftime('%Y-%m-%d'),0
    elif chinese_time == "去年":
        # 返回去年的第一天
        return f"{now.year - 1}-01-01",0
    elif chinese_time == "现在":
        # 返回当前日期
        return now.strftime('%Y-%m-%d'),1
    elif chinese_time.endswith("年"):
        year_str = chinese_time[:-1]  # 去掉“年”字
        # 处理公元前的年份
        if year_str.startswith("公元前"):
            year = 1000 * 1
        else:
            year = int(year_str)
        # 返回该年份的第一天
        return f"{year}-01-01",1
    else:
        return chinese_time,0



def is_valid_date(date_str, start_or_end_time=None):
    try:
        assert isinstance(date_str, str), "isinstance(date_str, str)"
        if date_str != "":
            try:
                date_str, flag = convert_chinese_time_to_date(date_str)
                if flag > 0:
                    return True, date_str
                # 尝试按照"yyyy-mm-dd"的格式解析字符串
                datetime.datetime.strptime(date_str, '%Y-%m-%d')
                return True, date_str
            except:
                assert start_or_end_time is not None, "start_or_end_time is not None"
                local_vars = {}
                exec(
                    "from datetime import datetime\nfrom datetime import timedelta\n" + date_str,
                    {"NOW_TIME": datetime.now()},
                    local_vars
                )
                datetime.strptime(local_vars[start_or_end_time], '%Y-%m-%d')
                return True,  "from datetime import datetime\nfrom datetime import timedelta\n" + date_str  # 解析成功，返回True
        else:
            return False, ""  # 解析失败，返回False

    except Exception as e:
        print(e)
        print(traceback.print_exc())
        return False, ""  # 解析失败，返回False


def time_calibration(question, start_time, end_time):
    now = datetime.datetime.now()
    today = now.strftime('%Y-%m-%d')

    if '今天' in question or "现在" in question or "此时" in question or "此刻" in question or "目前" in question or "今日" in question:
        start_time = today
        end_time = today
    elif '昨天' in question:
        yesterday = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        start_time  = yesterday
        end_time = yesterday
    elif '最近' in question or '近期' in question:
        start_time = (now - datetime.timedelta(days=now.weekday() + 10)).strftime('%Y-%m-%d')
        end_time = (now - datetime.timedelta(days=now.weekday() + 1)).strftime('%Y-%m-%d')
    elif '明天' in question:
        tomorrow = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        start_time = end_time = tomorrow
    elif '本周' in question:
        start_time = (now - datetime.timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        end_time = (now + datetime.timedelta(days=6 - now.weekday())).strftime('%Y-%m-%d')
    elif '上一周' in question:
        start_time = (now - datetime.timedelta(days=now.weekday() + 7)).strftime('%Y-%m-%d')
        end_time = (now - datetime.timedelta(days=now.weekday() + 1)).strftime('%Y-%m-%d')
    elif '下一周' in question:
        start_time = (now + datetime.timedelta(days=7 - now.weekday())).strftime('%Y-%m-%d')
        end_time = (now + datetime.timedelta(days=13 - now.weekday())).strftime('%Y-%m-%d')
    elif '本月' in question:
        start_time = now.replace(day=1).strftime('%Y-%m-%d')
        end_time = (now.replace(month=now.month % 12 + 1, day=1) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif '上一个月' in question:
        first_day_last_month = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        start_time = first_day_last_month.strftime('%Y-%m-%d')
        end_time = (now.replace(day=1) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif '下一个月' in question:
        first_day_next_month = (now.replace(month=now.month % 12 + 1, day=1))
        start_time = first_day_next_month.strftime('%Y-%m-%d')
        end_time = (first_day_next_month.replace(month=first_day_next_month.month % 12 + 1) - datetime.timedelta(
            days=1)).strftime('%Y-%m-%d')
    elif '上半年' in question:
        if now.month <= 6:
            start_time = (now.replace(year=now.year - 1, month=1, day=1)).strftime('%Y-%m-%d')
            end_time = (now.replace(year=now.year - 1, month=6, day=30)).strftime('%Y-%m-%d')
        else:
            start_time = now.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_time = now.replace(month=6, day=30).strftime('%Y-%m-%d')
    elif '下半年' in question:
        if now.month <= 6:
            start_time = now.replace(month=7, day=1).strftime('%Y-%m-%d')
            end_time = now.replace(month=12, day=31).strftime('%Y-%m-%d')
        else:
            start_time = (now.replace(year=now.year + 1, month=7, day=1)).strftime('%Y-%m-%d')
            end_time = (now.replace(year=now.year + 1, month=12, day=31)).strftime('%Y-%m-%d')
    elif '今年' in question:
        start_time = now.replace(month=1, day=1).strftime('%Y-%m-%d')
        end_time = now.replace(month=12, day=31).strftime('%Y-%m-%d')
    elif '去年' in question:
        start_time = now.replace(year=now.year - 1, month=1, day=1).strftime('%Y-%m-%d')
        end_time = now.replace(year=now.year - 1, month=12, day=31).strftime('%Y-%m-%d')
    elif '过去十年' in question:
        start_time = now.replace(year=now.year - 10).strftime('%Y-%m-%d')
        end_time = today
    elif '过去三年' in question:
        start_time = now.replace(year=now.year - 3).strftime('%Y-%m-%d')
        end_time = today
    elif '过去两年' in question:
        start_time = now.replace(year=now.year - 2).strftime('%Y-%m-%d')
        end_time = today
    elif '过去五年' in question:
        start_time = now.replace(year=now.year - 5).strftime('%Y-%m-%d')
        end_time = today

    elif "年" in question or "月" in question or "日" in question or "分" in question :
        pass
    elif not (re.search(r'\d', question) and ("年" in question or "月" in question or "日" in question or "分" in question)):
        start_time = ""
        end_time = ""
    return start_time,end_time


def get_retrieval_range_func(question: str, origin_question: str, session_id: str, pro_flag: bool = True):
    log.info("开始关键词抽取模块！！问题是:{}".format(question))

    if pro_flag:
        model_name = RagQAConfig['TASK_MODEL_CONFIG']["retrival_range"]
        # 载入预定义的PROMPT模版
        instruction_temp = PromptConfig["retrival_range_new"]["instruction"]
        prompt = instruction_temp.format(question, time.strftime("%Y年%m月%d日", time.localtime()))
        response = llm_call(
            query=prompt,
            model_name=model_name,
            # model_name="qwen2_57b_a14b_instruct_vllm",
            n=5,
            session_id=session_id
        )
        for response_i in response:
            try:
                retrieval_range = post_processing_llm_results(origin_question, response_i)
                question_supplement = None
                # question_supplement = get_question_supplement(
                #     context.get_question(),
                #     model_name=RagQAConfig['TASK_MODEL_CONFIG']['get_question_supplement'])
                # 新华社2024年5月31日新增加需求 唐波增加
                retrieval_range["keyword_all"] = retrieval_range["character"]
                retrieval_range["keywords"].extend(retrieval_range["location"])
                retrieval_range["keywords"] = list(set(retrieval_range["keywords"]))
                # rag_qa_context.set_question_supplement(question_supplement)
                # log.info("question_supplement:{}".format(question_supplement))
                retrieval_range["supplement"] = question_supplement
                return retrieval_range
            except Exception:
                # 获取traceback字符串
                error_message = traceback.format_exc()
                # 现在可以打印或将其存储到日志文件中
                log.error(error_message)
                return DEFAULT_JSON
        return DEFAULT_JSON
    else:
        return DEFAULT_JSON


def post_processing_llm_results(question,llm_response):
    try:
        log.info("llm response is: {}".format(llm_response))
        data_dict = ast.literal_eval(llm_response.replace(r"```json", "").replace("```", ""))
        llm_response = json.dumps(data_dict, indent=2, ensure_ascii=False)
        response_json = json.loads(llm_response)
        # assert '人物' in response_json, "'人物' in response_json"
        # assert '地点' in response_json, "'地点' in response_json"
        assert '关键词' in response_json, "'关键词' in response_json"
        assert '材料开始时间' in response_json, "'材料开始时间' in response_json"
        assert '材料结束时间' in response_json, "'材料结束时间' in response_json"

        retrieval_range = {
            "character": response_json.get('人物', []),
            "location": response_json.get('地点', []),
            "keywords": response_json['关键词'],
            "start_time": response_json['材料开始时间'],
            "end_time": response_json['材料结束时间'],
        }

        if not isinstance(retrieval_range["character"], list):
            retrieval_range["character"] = []
        if not isinstance(retrieval_range["location"], list):
            retrieval_range["location"] = []
        if not isinstance(retrieval_range["keywords"], list):
            retrieval_range["keywords"] = []

        start_time = is_valid_date(retrieval_range["start_time"], "start_date")[1]
        end_time = is_valid_date(retrieval_range["end_time"], "end_date")[1]
        curr_time = datetime.datetime.now()
        if start_time != "":
            # 确保检索时间都早于或等于当前时间
            if (curr_time - datetime.datetime.strptime(start_time, '%Y-%m-%d')).days < 0:
                start_time = ''
                end_time = ''
            else:
                # 结束时间为空或晚于当前时间，则结束时间为当前时间
                if end_time == "" or (curr_time - datetime.datetime.strptime(end_time, '%Y-%m-%d')).days < 0:
                    end_time = curr_time.strftime("%Y-%m-%d")
        if start_time == end_time and start_time == str(time.strftime("%Y-%m-%d", time.localtime())) and "今天" not in question:
            start_time=""
            end_time=""
        log.info("retrieval_range:{}".format(retrieval_range))
        # start_time,end_time = time_calibration(question,start_time,end_time)
        retrieval_range["start_time"] = start_time
        retrieval_range["end_time"] = end_time


        return retrieval_range
    except Exception as e:
        # 获取traceback字符串
        error_message = traceback.format_exc()
        # 现在可以打印或将其存储到日志文件中
        log.error(error_message)
        return {
            "character": [],
            "location": [],
            "keywords": [],
            "start_time": "",
            "end_time": "",
        }

@timer_decorator
def get_retrieval_range_task(context: RagQAContext):
    """
        接口请求参数
        RagQAContext:
            self._session_id string 会话id，用于标识同一个会话窗口内的问题
            self._dialog = {
                question_id: {
                    request_id string 单次请求的id（每请求一次接口都有一个独立的request_id）
                    question_id string 问题id
                    question string 用户输入问题
                }
            }  # 会话历史
    """
    try:
        assert context.get_session_id() is not None, log.error("请求session为空")
        assert context.get_request_id() is not None, log.error("请求request_id为空")
        assert context.get_question_id() is not None, log.error("请求question_id为空")
        assert context.get_question() is not None, log.error("请求question为空")

        question=context.get_question()
        rag_qa_context=context
        rag_qa_context.set_retrieval_range(DEFAULT_JSON)
        log.info("开始关键词抽取模块！！问题是:{}".format(question))

        retrieval_range = get_retrieval_range_func(question, context.get_origin_question(), context.get_session_id(),
                                                   context.get_single_question().get_pro_flag())
        if retrieval_range:
            log.info("\n In task Get Retrieval Range, the final retrieval_range is: \n{}".format(retrieval_range))
            log.info("完成抽取关键词，开始存数据到Context并返回数据")
            return_val = json.dumps({
                "is_success": True,
                "return_code": RagQAReturnCode.FUNCTION_RUN_SUCCESS,
                "result": retrieval_range,
                "timestamp": str(time.time()),
                "err_msg": "",
                "session_id": context.get_session_id()
            }, ensure_ascii=False)
            rag_qa_context.set_retrieval_range(retrieval_range)
        else:
            # 获取traceback字符串
            error_message = traceback.format_exc()
            # 现在可以打印或将其存储到日志文件中
            log.error(error_message)
            return_val = json.dumps({
                "is_success": False,
                "return_code": RagQAReturnCode.UNKNOWN_ERROR,
                "result": DEFAULT_JSON,
                "timestamp": str(time.time()),
                "err_msg": str(error_message),
                "session_id": context.get_session_id()
            }, ensure_ascii=False)
            rag_qa_context.set_retrieval_range(DEFAULT_JSON)
        return return_val
    except Exception as e:
        return_val = json.dumps({
            "is_success": False,
            "return_code": RagQAReturnCode.UNKNOWN_ERROR,
            "result": DEFAULT_JSON,
            "timestamp": str(time.time()),
            "err_msg": str(traceback.print_exc()),
            "session_id":context.get_session_id()
        }, ensure_ascii=False)
        rag_qa_context.set_retrieval_range(DEFAULT_JSON)
        return return_val


if __name__ == '__main__':
    for question in open("../../data/qa/waic.txt", "r"):
        # question = "在中部地区崛起座谈会上,习近平总书记对企业家有何期望?"
        question="男朋友的官宣文案有点高级，我该怎么写一个这样的文案才能配得上？"
        rag_qa_context = RagQAContext(session_id=question)
        rag_qa_context.add_single_question("request_id", "question_id", question)
        res = get_retrieval_range_task(rag_qa_context)
        log.warning("{}:{} ".format(question, json.loads(res)["result"]))
        break
