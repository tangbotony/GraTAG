from tqdm import tqdm
from include.utils.text_utils import get_md5
from include.context import DocQAContext
from modules.further_question_recommend_group.further_question_recommend_group import FurtherQuestionRecommendTask


class FurtherQuestionRecommendDocTask(FurtherQuestionRecommendTask):
    """ 追问问题推荐 task
        必传入参:
            session_id = context.get_session_id()
            request_id = context.get_request_id()
            question_id = context.get_question_id()
            question = context.get_question()
            answer = context.get_answer()
            history_questions = context.get_history_questions()#历史问题
        获取本模块执行结果
            - 追问问题推荐:["习近平何时就职？", "习近平最近访问的国家有哪些?"]
            context.get_further_recommend_questions
    """
    def __init__(self, doc_qa_context: DocQAContext):
        super().__init__(doc_qa_context)


if __name__ == "__main__":
    test_question_list = [{"question": "今天上海有什么新闻? 其中哪些是关于房地", "answer": ""},{"question": "分析中国金融部门在维护金融稳定和促进经济发展中，如何平衡风险防控和金融创新。",
                           "answer": """中国金融部门将金融稳定的定义涵盖了政治保障、利率、汇率、流动性支持等多个方面，
                           同时强调了金融风险监测和处置的协调机制的重要性[2XBHxjWY]。在风险防控方面，采取了包括维护金融稳定职责的多种措施，
                           如强化金融基础设施和制度建设，提高会计和审计标准，完善公司治理和信用制度建设[jHMR9ZkX]。为了平衡风险防控和金融创新，
                           中国金融部门坚持市场化、法治化轨道上推进金融创新，通过数据化方式提升风险管理能力，优化资源配置，增强金融服务供给能力，同时加强对新型金融产品和业务的审慎监管[av0QND3d]。"""}]
    results = []
    for i in tqdm(range(len(test_question_list[:1]))):
        session_idx = "mock_session_{}".format(i)
        context = DocQAContext(session_id=get_md5(session_idx))
        context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                    question_id=get_md5("{}_qe".format(session_idx)), question=test_question_list[i]["question"][:512])
        context.set_answer(final_answer=test_question_list[i]["answer"] ,question_id=get_md5("{}_qe".format(session_idx)))
        response = FurtherQuestionRecommendTask(context).get_further_question_recommend()
        test_question_list[i].update({"further_quetions": context.get_further_recommend_questions()})
        print("context.get_further_recommend_questions:{}".format(context.get_further_recommend_questions()))