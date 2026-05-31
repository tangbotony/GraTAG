import time
from include.logger import time_log
from include.context import RagQAContext
import inspect
import json
from functools import wraps
# from include.utils.webhook_utils import WEBHOOK_SECRET, LarkBot


# time_lark_bot = LarkBot(WEBHOOK_SECRET)

def timer_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        context = None
        for item in args:
            try:
                if isinstance(item, RagQAContext):
                    context = item
                    break
                if isinstance(item.context, RagQAContext):
                    context = item.context
                    break  
            except:
                pass
        end_time = time.time()
        cost_time = end_time - start_time
        module_name = inspect.getmodule(func).__name__
        if context is not None:
            time_log.info(json.dumps({"session_id": context.get_session_id(), "request_id": context.get_question_id(), "module_name": module_name + "." + func.__name__, "cost_time": cost_time}, ensure_ascii=False))
            # time_log.info(f"{context.get_session_id()}--{context.get_question_id()}: {module_name}.{func.__name__}的执行时间是: {end_time - start_time}秒")
        else:
            time_log.info(json.dumps({"module_name": module_name + "." + func.__name__, "cost_time": cost_time}, ensure_ascii=False))
        return result

    return wrapper

def log_time(session_id, request_id, module_name, cost_time, user_id=None):
    time_log.info(json.dumps({"session_id": session_id, "request_id": request_id, "module_name": module_name, "cost_time": cost_time}, ensure_ascii=False))
    if user_id:
        send_data = '''- **session_id: {}**\n- **request_id: {}**\n- **cost_time: {}**\n- **user id: {}** \n'''.format(session_id, request_id, cost_time, user_id)
        # time_lark_bot.send_card(user_id, module_name, send_data)

class Timer:
    def __init__(self, session_id, request_id, module_name, user_id):
        self.session_id = session_id
        self.request_id = request_id
        self.module_name = module_name
        self.user_id = user_id

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        cost_time = self.end_time - self.start_time
        time_log.info(json.dumps({"session_id": self.session_id, "request_id": self.request_id, "module_name": self.module_name, "cost_time": cost_time}, ensure_ascii=False))
        send_data = '''- **session_id: {}**\n- **request_id: {}**\n- **cost_time: {}**\n- **user id: {}** \n'''.format(self.session_id, self.request_id, cost_time, self.user_id)
        # time_lark_bot.send_card(self.user_id, self.module_name, send_data)

def timer_logger_decorator(module_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                raise e
            end_time = time.time()
            cost_time = end_time - start_time
            time_log.info(json.dumps({"module_name": module_name, "cost_time": cost_time}, ensure_ascii=False))
            return result

        return wrapper
    return decorator