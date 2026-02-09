class RagQAReturnCode:
    FUNCTION_RUN_SUCCESS = "10000"  # 接口调用成功统一状态码
    UNKNOWN_ERROR = "10001"  # 未知错误统一状态码
    LLM_ERROR = "10002"   # 大模型调用失败统一状态码
    QUESTION_REJECTION_ERROR = "10003"  # 问题拒答判断出错
    QUESTION_SUPPLEMENT_ERROR = "10004"  # 问题补全判断出错
    QUESTION_RECOMMEND_ERROR = "10005"  # 问题推荐出错
    QUESTION_FUR_RECOMMEND_ERROR = "10006"  # 追问问题推荐出错
    REINFORCE_QUESTION_ERROR = '10007'  # 问题增强出错
    TIMELINE_QUERY_REWRITE_ERROR = '10008'  # 时间线问题改写出错
    QUERY_RECOMMEND_ERROR = "10009"  # query推荐出错
    TIMELINE_REMOVE_DUPLICATED_EVENT_ERROR = '10009'  # 时间线事件去重排序出错
    TIMELINE_HIGHLIGHT_EXTRACT_ERROR = '10010'  # 时间线事件highlight提取出错
    TIMELINE_GROUP_ERROR='10011'    # 时间线pipeline出错
    TIMELINE_EVENT_EXTRACT_ERROR = '10012'  # 时间线事件抽取出错
    TIMELINE_GRANULARITY_ERROR = "10013"  # 时间线粒度判断出错
    TIMELINE_REFERENCE_ERROR = "10014" # 时间线reference提取出错