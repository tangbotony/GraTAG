from .common_config import CommonConfig


class TimeLineConfig(CommonConfig):
    def __init__(self):
        super().__init__()
        self.__dict__.update({
            # 任务对应模型对应"MODEL_CONFIG" key
            "TIMELINE_TASK_MODEL_CONFIG": {
                "query_rewrite": "memory25_14b",
                "event_info_extract": "memory25_14b",
                "hightlight_extract": "memory25_14b",
                "granularity": "memory25_14b",
                "top_p": 0.1,
                "temperature":0.0,
                "max_try_cnt":1
            },
            "TIMELINE_TASK_PARAMS_CONFIG": {
                "event_info_extract": {
                    "longchunk_pre_search_len":1000,
                },
                "extract_reference_threshold": 0.0,
                "extract_reference_nums": 50,
                "remove_duplicated_day":32,#去重计算天数范围，默认如果是范围内的事件会做去重
                "use_longchunk": False,
                "event_duplicated_threshold":0.75 #事件去重相似度阈值
            },
            "TIMELINE_PIPELINE_PARAMS": {
                "use_timeline": True, # 是否开启timeline
                "use_qa_dag": True, # 是否和qa使用同一个dag
                "wait_qa_time":60, # 等待qa recall的最长时间
            },
            "TIMELINE_WHITE_LIST_CONFIG": {
                "scheme_id": "fee0e638-ae2d-4220-8089-db29f23affb5",
            },
            "TIMELINE_WHITE_LIST_QUERY_EXPANSION":{
                "threshold":0.8,
                "expansion":{
                "关于“姜萍”这一热点事件，大家的看法是什么？":[
                    "姜萍事件始末",
                    "姜萍事件进展怎么样了",
                    "姜萍为什么遭到这么多质疑",
                    "姜萍到底作弊了吗",
                    "姜萍为什么火了"
                ],
                "请详细分析“于欢案”案件始末，以及相关法条的情况":[
                    "于欢案最终审判结果如何",
                    "请评估“于欢案”对中国法律制度改革和司法解释的推动作用",
                    "请分析“于欢案”中涉及的主要当事人的行为及其法律责任。",
                    "于欢案事件始末",
                    "于欢案经历了哪些反转"
                ],
                "新能源汽车产业的进展和新闻有那些，其能否替代房地产成为新支柱产业？":[
                    "房地产和新能源汽车产业哪个更有可能成为未来新的支柱产业？",
                    "新能源汽车有可能替代房地产吗",
                    "房地产行业是否有可能被新能源汽车替代成为新的产业",
                    "新能源汽车行业怎么样，会不会取代房地产",
                    "我国新能源汽车发展前景，未来会超越房地产吗"
                ],
                }
            }

        }
        )
