from .common_config import CommonConfig


class QueryIntentRecognitionConfig(CommonConfig):
    def __init__(self):
        super().__init__()
        self.__dict__.update({
            # 任务对应模型对应"MODEL_CONFIG" key
            "API_SERVICE": True,
            "API_SERVICE_CONFIG": {
                "url": "https://apigateway.online.xinyunews.cn/intent/intent_recognition",
                "token": "xxx",
                "request_func": ["query_translate", "query_reject", "query_supply", "query_related_event"]
            },
            # 任务对应模型对应"MODEL_CONFIG" key
            "WHITE_LIST": False,
            "TASK_MODEL_CONFIG": {
                "query_reject": "memory25_72b",
                "query_supplement": "memory_72b_0807sft_vllm",
                "query_reinforce": "memory_72b_0807sft_vllm",
                "query_keyword": "memory_72b_0807sft_vllm",
                "query_translate": "memory25_14b",
                "hot_events_related_query": "memory25_72b"
            },
            "WHITE_LIST_CONFIG": {
                "query_intent_recognition": {"scheme_id": "b9a5229b-f48d-4d5e-88bf-de861cce8790"},
                "query_reinforce": {"scheme_id": "2c98d445-db2d-4424-b78d-b5120e00b2b6"},
            },
            "SUMMARY_SEARCH_CONFIG": {
                "url": "xxx",
                "token": "xxx",
                "time_range": 30,
                "return_num": 20,
            },
            "HOT_QUESTION_SEARCH_CONFIG": {
                "sim_threshold": 0.6,
                "time_range": 60
            }
        }
        )
