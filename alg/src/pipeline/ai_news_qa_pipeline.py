from concurrent.futures import ThreadPoolExecutor

from modules import *
from include.context import RagQAContext
from include.utils.text_utils import get_md5
from include.logger import ContextLogger


def callQA(context: RagQAContext):
    ContextLogger(context).info("callQA")
    # get_graph_recall(self, graph: IGraph,
    RecallTask(context).get_graph_recall(application='QuestionAnswer', graph=context.get_multi_hop_rag_queries())
    QueryAnswerTask(context).get_query_answer()


if __name__ == "__main__":
    for query in open("../data/qa/questions.txt", "r"):
        context = RagQAContext(session_id=get_md5(query))
        context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
        IntentionUnderstandingTask(context).get_intention()
        QueryDivisionBasedCoTTask(context).get_cot(
            use_scene="general", if_parallel=True, split_num_threshold=3)
        threadPool = ThreadPoolExecutor(max_workers=50, thread_name_prefix="test_")
        all_task = [threadPool.submit(callQA, context),threadPool.submit(TimelineTask(context).get_timeline)]
        break




