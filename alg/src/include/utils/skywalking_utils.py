import os
from skywalking import agent
from skywalking import config as sk_config
from skywalking.trace.tags import Tag
from skywalking.trace.context import get_context
import inspect
from functools import wraps
from typing import List
from skywalking import Layer, Component
from skywalking.trace.context import get_context
from skywalking.trace.tags import Tag
import threading
from include.config import CommonConfig

class TagLogic(Tag):
    key = 'x-le'

disable = CommonConfig['SW_CONFIGS']['disable']
skywalking_url = CommonConfig['SW_CONFIGS']['server_url']
skywalking_service_name = CommonConfig['SW_CONFIGS']['service_name']
skywalking_instance_name = CommonConfig['SW_CONFIGS']['instance_name']
os.environ["SW_AGENT_DISABLE_PLUGINS"] = "sw_pymongo,sw_elasticsearch,sw_requests"
os.environ['SW_AGENT_DISABLED'] = disable

# 注册sw客户端，开始运行
def start_sw():
    if disable == "false":
        sk_config.init(agent_collector_backend_services=skywalking_url,
                    agent_name=skywalking_service_name,
                    agent_instance_name=skywalking_instance_name,
                    agent_log_reporter_active=True,
                    agent_log_reporter_level = "INFO")
        agent.start()

class TagLogicEndPoint(Tag):
    
    def __init__(self):
        self.key = "x-le"
        super().__init__('{"logic-span":true}')
        
import os
SW_AGENT_DISABLED: bool = os.getenv('SW_AGENT_DISABLED', '').lower() == 'true'
# print(os.getenv('SW_AGENT_DISABLED', '').lower())
print(f"SW_AGENT_DISABLED: {SW_AGENT_DISABLED}")

CONST_PARENT_TID = "SW_P_TID:"
_snapshots = {}
lock = threading.Lock()

def printSS():    
    print(f"snapshot len: {len(_snapshots)}")

def addSnapshot(tid,ss):
    global _snapshots
    with lock:
        _snapshots[tid] = ss
        # printSS()
        
def delSnapshot(tid):
    global _snapshots
    with lock:
        if tid in _snapshots.keys():
            del _snapshots[tid]
            # printSS()

def findSnapshot(tid):
    global _snapshots
    with lock:
        return _snapshots.get(tid,None)
    

def record_thread():
    return f"{CONST_PARENT_TID}{threading.get_ident()}"

def pick_ptid(args):    
    with_ptid = False
    ptid = None
    if args:
        if len(args)>0:
            para = args[-1]
            if isinstance(para, str):
                if para.startswith(CONST_PARENT_TID):
                    with_ptid = True
                    ptid = int(para.replace(CONST_PARENT_TID,""))
    return with_ptid,ptid

def trace_new(
        op: str = None,
        layer: Layer = Layer.Unknown,
        component: Component = Component.Unknown,
        tags: List[Tag] = None,
        logic_ep:bool = False,
):
    def decorator(func):
        _op = op or func.__name__

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if SW_AGENT_DISABLED:
                    return await func(*args, **kwargs)

                context = get_context()
                span = context.new_local_span(op=_op)
                span.layer = layer
                span.component = component
                if tags:
                    for tag in tags:
                        span.tag(tag)
                if logic_ep:
                    span.tag(TagLogicEndPoint())
                with span:
                    return await func(*args, **kwargs)

            return wrapper

        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with_ptid,ptid = pick_ptid(args)
                if with_ptid:
                    args = args[0:-1]
                    if not SW_AGENT_DISABLED:
                        ss = findSnapshot(ptid)

                if SW_AGENT_DISABLED:
                    return func(*args, **kwargs)

                context = get_context()

                tid = threading.get_ident()
                # print(f"{op} {func.__name__} trace wrapper tid {tid}")
                snapshot = context.capture()
                addSnapshot(tid,snapshot)

                span = context.new_local_span(op=_op)
                span.layer = layer
                span.component = component    
                if tags:
                    for tag in tags:
                        span.tag(tag)
                if logic_ep:
                    span.tag(TagLogicEndPoint())
                with span:
                    if with_ptid:
                        context.continued(ss)
                        
                    ret = func(*args, **kwargs)                     
                    delSnapshot(tid)
                    return ret

            return wrapper

    return decorator
