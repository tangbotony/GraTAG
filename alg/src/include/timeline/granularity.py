import traceback

from include.config import TimeLineConfig, PromptConfig
from include.logger import log
from include.utils import llm_call


def get_granularity(timeline_question,
                    model_name=TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["granularity"],
                    clogger=log,
                    session_id=''):
    retry_cnt = 0
    max_retry_cnt = 3
    granularity = None
    if 'qwen' in model_name:
        task_prompt_template = PromptConfig["timeline_granularity"]["QWEN_input_item"] #QWEN_input_item or GPT_input_item
    else:
        task_prompt_template = PromptConfig["timeline_granularity"]["GPT_input_item"] #QWEN_input_item or GPT_input_item
    prompt = task_prompt_template.format(timeline_question)
    while True:
        try:
            response = llm_call(query=prompt, model_name=model_name, clogger=clogger, session_id=session_id)
            response = response.strip()

            if response.endswith("年"):
                granularity = "年"
            elif response.endswith("季度") or response.endswith("季"):
                granularity = "季"
            elif response.endswith("月"):
                granularity = "月"
            elif response.endswith("周") or response.endswith("星期"):
                granularity = "周"
            elif response.endswith("天") or response.endswith("日"):
                granularity = "日"
            break
        except Exception as e:
            if retry_cnt == max_retry_cnt:
                clogger.warning("get_granularity occur error: {}, retry cnt: {}/{}, return None."
                                .format(e, retry_cnt, max_retry_cnt)
                                )
                granularity = None
                break
            retry_cnt += 1
            clogger.warning("get_granularity occur error: {}, will retry, retry cnt: {}/{}"
                            .format(traceback.format_exc(), retry_cnt, max_retry_cnt)
                            )
    return granularity


if __name__ == "__main__":
    timeline_question = "请提供一份2024年上半年我国金融统计数据的月度对比分析"
    granularity = get_granularity(timeline_question)
    print(granularity)
