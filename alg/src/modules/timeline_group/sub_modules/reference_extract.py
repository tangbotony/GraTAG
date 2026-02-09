import sys
import time
import traceback
import json
import random
from include.context import RagQAContext
from include.logger import log
from include.logger import ContextLogger
from include.context import RagQAReturnCode
from include.timeline import get_rewrite_query
from include.config import PromptConfig, TimeLineConfig
import traceback
from include.utils.text_utils import get_md5
from include.utils.skywalking_utils import trace_new, start_sw
from include.utils.timeline_utils import extract_reference,extract_chunk_reference,add_dag_node_ref
from include.utils.Igraph_utils import IGraph, ArcNode
from include.decorator import timer_decorator

class ReferenceExtract:
    """
    时间线问题改写模块
    必传入参
        ori_query = self.context.get_question()
        question_id = self.context.get_question_id()
        supplement_info = self.context.get_question_supplement()


    获取本模块执行结果
        - 时间线问题重写结果:{"is_timeline_query":False ,"dimension":"xx","timeline_queries":["xx","xx","xx"]}
        context.get_timeline_rewrite_query()

    """

    def __init__(self, rag_qa_context: RagQAContext):
        self.context = rag_qa_context
        self.clogger = ContextLogger(self.context)

    @trace_new(op="get_timeline_reference")
    @timer_decorator
    def get_timeline_reference(self, context=None):
        log.info("开始时间线参考资料抽取模块！")
        try:
            assert self.context.get_session_id() is not None, "session_id为空"
            assert self.context.get_request_id() is not None, "request_id为空"
            assert self.context.get_question_id() is not None, "question_id为空"
            assert self.context.get_question() is not None and len(self.context.get_question()) != 0, "question为空"

            beginning_time = time.time()
            # 获取必要入参
            question_id = self.context.get_question_id()
            dags = self.context.get_timeline_dag(question_id)
            # 使用qa的dag图时，原始问题的ref存在context里
            external_ref=self.context.get_origin_ref()
            if external_ref:
                new_query = self.context.get_timeline_new_query()
                add_dag_node_ref(dags,external_ref,new_query)
            reference_dict=extract_reference(dags, reference_threshold=TimeLineConfig["TIMELINE_TASK_PARAMS_CONFIG"]["extract_reference_threshold"])
            reference_chunk_dict=extract_chunk_reference(dags)
            # 结果写入context
            self.context.set_timeline_reference(reference_dict,question_id)
            self.context.set_timeline_chunk_reference(reference_chunk_dict, question_id)
            self.clogger.info(
                "timeline_reference_extract success, use time {}s".format(round(time.time() - beginning_time, 2)))
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            is_success = True
            error_detail = {}
            err_msg = ''

        except Exception as e:
            self.clogger.error(traceback.format_exc())
            is_success = False
            return_code = RagQAReturnCode.TIMELINE_REFERENCE_ERROR
            error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
            err_msg = str(e)
        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)

if __name__ == "__main__":
    start_sw()
    reference_info={
        "query": "北京在获得2008年奥运会举办权后立即宣布了哪些筹备计划？",
        "reference": {
            "[jfTRtHZg]": {
                "id": "jfTRtHZg",
                "description": "并最重同土耳其的伊斯坦布尔、日本的大阪、法国的巴黎、加拿大的多伦多共五个城市成为2008年第29届奥运会的候选城市。   最终国际奥委会投票选定北京获得2008年奥运会主办权。我们的首都这次申奥笑到了最后，随后国际奥委会主席萨马兰奇在莫斯科宣布，北京成为2008年奥运会主办城市。当天晚上北京申奥成功的消息传来，北京数十万群众涌向天安门举行狂欢，以表达心中的无比喜悦。 《天津青年》杂志在百年前就提出“中国什么时候能举办奥运会？”站在北京奥运会开幕的历史时刻，回望两度申奥、七年筹备，世人惊叹于中国的改变。这一天，中国人的梦想终于实现。",
                "title": "历史上的今天，2008年第29届北京奥运会开幕！",
                "url": "https://baijiahao.baidu.com/s?id=1641285936243867406&wfr=spider&for=pc",
                "theme": "北京在获得2008年奥运会举办权后立即宣布了哪些筹备计划？",
                "source": "SEARCH_TYPE_IAAR_DATABASE",
                "source_id": "18add8373366ed5f03d9ac5314f03e73",
                "other_info": {
                    "author": "",
                    "title": "历史上的今天，2008年第29届北京奥运会开幕！",
                    "publish_time": "2019-08-08 08:17:00",
                    "images": [
                        {
                            "above_content": "",
                            "below_content": "<span class=\"bjh-p\">历史上的今天 ，第29届奥林匹克运动会于2008年8月8日至24日在中国首都北京举行。此次奥运设置了三大理念：绿色奥运、科技奥运 、人文奥运。举行了28个大项，38个分项的比赛，产生302枚金牌。</span>",
                            "oss_id": "img/f7fe4e00d3449f8a4e45cfc62255e91b.jpg",
                            "url": "https://pics5.baidu.com/feed/b90e7bec54e736d1ef3a113f42ab0fc7d46269d9.jpeg@f_auto?token=99976655a4ea1194b82283ef6cf7323c&s=DAB308C632E2D35D507ABFBF0300900D"
                        },
                        {
                            "above_content": "<span class=\"bjh-p\">历史上的今天 ，第29届奥林匹克运动会于2008年8月8日至24日在中国首都北京举行。此次奥运设置了三大理念：绿色奥运、科技奥运 、人文奥运。举行了28个大项，38个分项的比赛，产生302枚金牌。</span>",
                            "below_content": "<span class=\"bjh-p\">早在1993年，我国就申请举办2000年第27届奥林匹克运动会，但在最后以2票之差惜败于悉尼，1998年北京卷土重来再次提出申办2008年第29届奥林匹克运动会。</span>",
                            "oss_id": "img/d1c65421f53644b118d4a716e719e846.jpg",
                            "url": "https://pics1.baidu.com/feed/f603918fa0ec08fa35c2928e81157d6857fbdade.jpeg@f_auto?token=3feceb7c4377c3ed79df23f137fa2c3e&s=3391F3A6949B9FCC7B56C80E030060DB"
                        },
                        {
                            "above_content": "<span class=\"bjh-p\">并最重同土耳其的伊斯坦布尔、日本的大阪、法国的巴黎、加拿大的多伦多共五个城市成为2008年第29届奥运会的候选城市。<span class=\"bjh-br\"></span></span>",
                            "below_content": "<span class=\"bjh-p\">最终国际奥委会投票选定北京获得2008年奥运会主办权。我们的首都这次申奥笑到了最后，随后国际奥委会主席萨马兰奇在莫斯科宣布，北京成为2008年奥运会主办城市。当天晚上北京申奥成功的消息传来，北京数十万群众涌向天安门举行狂欢，以表达心中的无比喜悦。</span>",
                            "oss_id": "img/93f2c06622476743fa40fef1bb72b405.jpg",
                            "url": "https://pics1.baidu.com/feed/902397dda144ad34904f3e3908594cf133ad8599.jpeg@f_auto?token=972d4ac71343629e9850750a4e632afa&s=17A5D8A26062B8EC3E5197BD03004001"
                        },
                        {
                            "above_content": "<span class=\"bjh-p\">最终国际奥委会投票选定北京获得2008年奥运会主办权。我们的首都这次申奥笑到了最后，随后国际奥委会主席萨马兰奇在莫斯科宣布，北京成为2008年奥运会主办城市。当天晚上北京申奥成功的消息传来，北京数十万群众涌向天安门举行狂欢，以表达心中的无比喜悦。</span>",
                            "below_content": "<span class=\"bjh-p\">《天津青年》杂志在百年前就提出“中国什么时候能举办奥运会？”站在北京奥运会开幕的历史时刻，回望两度申奥、七年筹备，世人惊叹于中国的改变。这一天，中国人的梦想终于实现。</span>",
                            "oss_id": "img/2172c5e8edd04e1c2dffbffd1822cdaa.jpg",
                            "url": "https://pics1.baidu.com/feed/c8ea15ce36d3d5398a003eb5e07ca955342ab083.jpeg@f_auto?token=ed3d3c087a53a7df870171d490b6149e&s=B75414CE6F67BA4D56654C2C0300A04B"
                        },
                        {
                            "above_content": "<span class=\"bjh-p\">《天津青年》杂志在百年前就提出“中国什么时候能举办奥运会？”站在北京奥运会开幕的历史时刻，回望两度申奥、七年筹备，世人惊叹于中国的改变。这一天，中国人的梦想终于实现。</span>",
                            "below_content": "<span class=\"bjh-p\">北京奥运会共打破43项新世界纪录及132项新奥运纪录，并破纪录共有87个国家在赛事中取得奖牌，中国以51面金牌成为居奖牌榜首名，是奥运历史上首个亚洲国家登上金牌榜首。</span>",
                            "oss_id": "img/b5700295519d18a48bb36b27e32048ce.jpg",
                            "url": "https://pics2.baidu.com/feed/500fd9f9d72a6059b9004f35f1cf749e023bba8a.jpeg@f_auto?token=7732612a30a6345a56f0dae9abd77a97&s=C57138C4D7F98A6D4E7CB08A0300E0CB"
                        }
                    ],
                }
            }
        }
    }

    i=0
    session_idx = "mock_session_{}".format(i)
    context = RagQAContext(session_id=get_md5(session_idx))
    context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                question_id=get_md5("{}_qe".format(session_idx)), question=reference_info["query"])
    dag = IGraph()

    tmp_query=reference_info["query"]
    tmp_reference_content=reference_info["reference"]
    x = ArcNode(tmp_query)
    dag.add_new_node(x)
    reference = tmp_reference_content
    dag.add_node_param(tmp_query, "reference", [], attr_type='list')
    dag[tmp_query].reference = reference
    context.set_timeline_dag(dag)
    context.set_timeline_new_query(tmp_query)
    ReferenceExtract(context).get_timeline_reference()
    print("context.get_timeline_reference:{}".format(context.get_timeline_reference()))
