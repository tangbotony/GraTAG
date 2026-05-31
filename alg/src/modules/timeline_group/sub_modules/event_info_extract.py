import sys
import time
import traceback
import json
import random
from include.context import RagQAContext
from include.context import RagQAReturnCode
from include.logger import log
from include.logger import ContextLogger
from include.timeline import getEventInfoWithDag
from include.utils.Igraph_utils import IGraph, ArcNode
from include.utils.text_utils import get_md5
from include.utils.skywalking_utils import trace_new, start_sw
from include.decorator import timer_decorator


class EventInfoExtract:
    """
    文档级别的事件信息抽取模块
    """
    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)

    @trace_new(op='get_event_info_extract')
    @timer_decorator
    def get_event_info_extract(self, context=None):
        log.info("开始事件信息抽取模块！")
        try:
            assert self.context.get_session_id() is not None, "session_id为空"
            assert self.context.get_request_id() is not None, "request_id为空"
            assert self.context.get_question_id() is not None, "question_id为空"
            assert self.context.get_question() is not None and len(self.context.get_question()) != 0, "question为空"
            assert self.context.get_timeline_dag(self.context.get_question_id()) is not None, "dag图为空"

            beginning_time = time.time()
            # 从图中得到节点，挨个遍历出结果
            dags = self.context.get_timeline_dag(self.context.get_question_id())
            new_query=self.context.get_timeline_new_query()
            retrieval_range = self.context.get_retrieval_range()
            getEventInfoWithDag(dags=dags, newQuery=new_query, clogger=self.clogger, retrieval_range=retrieval_range, session_id=self.context.get_session_id())

            self.clogger.info(
                "timeline_event_info_extra success, use time {}s".format(round(time.time() - beginning_time, 2)))
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''
        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_EVENT_EXTRACT_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)  
        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)

if __name__ == '__main__':
    start_sw()
    test_question = "习近平主席匈牙利国事访问行程"
    session_idx = "mock_session_0"
    context = RagQAContext(session_id=get_md5(session_idx))
    context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                question_id=get_md5("{}_qe".format(session_idx)), question=test_question)
    dag = IGraph()
    query1 = "习近平主席匈牙利国事访问行程"
    chunk1 = "在习近平主席对匈牙利进行国事访问期间，中匈双方达成多项合作共识。其中，关于布达佩斯中国文化中心启动运营的消息备受中匈各界关注。近日，总台记者走进了全新的布达佩斯中国文化中心，接下来，我们就一起来了解这个中匈文化交流的新平台。\n\n　　布达佩斯中国文化中心是根据中匈互设文化中心协定，由中国文化和旅游部在匈牙利设立的官方文化机构。在庭院中，设计人员巧妙地将苏州园林和匈牙利古典主义风格充分融合。无论是大方简洁的中式座椅、精心设置的中餐制作体验室、还是功能齐全的展览厅，都让中心所在的这座百年建筑散发出浓浓中国味。\n\n　　中国文化中心成了匈牙利的中国文化爱好者学习中文、了解中国丰富文化和旅游资源的重要平台。"
    longChunk1 = "在习近平主席对匈牙利进行国事访问期间，中匈双方达成多项合作共识。其中，关于布达佩斯中国文化中心启动运营的消息备受中匈各界关注。近日，总台记者走进了全新的布达佩斯中国文化中心，接下来，我们就一起来了解这个中匈文化交流的新平台。\n\n　　布达佩斯中国文化中心是根据中匈互设文化中心协定，由中国文化和旅游部在匈牙利设立的官方文化机构。在庭院中，设计人员巧妙地将苏州园林和匈牙利古典主义风格充分融合。无论是大方简洁的中式座椅、精心设置的中餐制作体验室、还是功能齐全的展览厅，都让中心所在的这座百年建筑散发出浓浓中国味。\n\n　　中国文化中心成了匈牙利的中国文化爱好者学习中文、了解中国丰富文化和旅游资源的重要平台。"
    publishTime1 = "2024-05-08 15:59"
    x = ArcNode(query1)
    dag.add_new_node(x)
    reference = {
        '[0000001]':
        {
            'id': '0000001',
            'description': chunk1,
            'url': 'www.baidu.com',
            'other_info': {
                'all_content': longChunk1,
                'publish_time':publishTime1
            }
        }
    }
    dag.add_node_param(query1, "reference", [], attr_type='list')
    dag[query1].reference = reference
    context.set_timeline_dag(dag, question_id=get_md5("{}_qe".format(session_idx)))
    context.set_timeline_new_query("习近平主席匈牙利国事访问行程")
    eventIE = EventInfoExtract(context)
    eventIE.get_event_info_extract()
    print(dag[query1].event_info)
