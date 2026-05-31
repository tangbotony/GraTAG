from .common_config import CommonConfig


class DocQAConfig(CommonConfig):
    def __init__(self):
        super().__init__()
        self.__dict__.update({
            # XX_MODEL_CONFIG 是基于CommonConfig.MODEL_CONFIG 对每个项目新增部署模型的调用配置
            # 每新增一个线上部署模型，需在llm_caller_utils增加对应call_xxxx函数，并在llm_caller_utils.get_llm_call_fun增加模型调用逻辑
            "RAG_MODEL_CONFIG": {
                "url": "xxx",
                "qwen14_qa_comm_11_v2": "qwen14_qa_comm_11_v2"
            },
            "FIG_CONFIG": {
                "url": "xxx",
                "url_duplicate": "xxx",
                'token': "xxx",
                "bucket_name": "public-crawler",
                "is_limit_candidate_image": "true",
                "limit_candidate_image_size": 60,
            },
            "CHART_UNDERSTANDING": {
                "url": "xxx",
                "token": "xxx",
                "path_prefix": "xxx"
            },
            "QA_QREINFORCE_QMultiHop_MODEL_CONFIG": {
                "url": "xxx",
                "qwen14_xinhua_rag_vllm": "qwen1514_xinhua_rag_vllm",
                "key": "xxx",
                "retry_time": 5
            },
            "TASK_MODEL_CONFIG": {
                'query_abstract': "gpt-4o",  # 文本摘要
                "question_supplement": "gpt-4o",  # 问题补充
                "question_reinforce": "memory25_14b",  # 问题增强
                "question_keyword": "memory25_14b",  # 问题关键词生成
                "generate_answer": "memory25_72b",  # 最终答案生成
                "generate_sub_answer": "memory25_72b",  # 子问题答案生成
                "retrival_range": "memory25_14b",  # 问题关键信息提取
                "get_question_supplement": "gpt-4o",  # 问题补充
                "check_dependency": "memory25_14b",  # 思维链
                "multihop_rewrite": "memory25_14b",  # 思维链
                "get_multi_hop_queries": "memory25_14b",  # 思维链
                "useful_reference": "gpt-4o",  # 行程类问题相关性判断
                "general_query_answer": "gpt-4o",  # 行程类问题问答
                "add_reference_to_answer": "gpt-4o"
            },
            "EXP_CONFIG": {
                'add_fig': "false",  # 是否在答案中调用图片
                'is_retrieval_range': "true",  # 是否采用retrieval range过滤reference
                'is_reinforce': "false",  # 是否采用问题增强
                'recall_rag': 'without_upstream',  # ['with_upstream', 'without_upstream']  是否在思维链下游子问题检索时拼接上游问题检索词
                'add_ref_to_final_answer_mode': 'all_ref',  # ['no_ref', 'ori_query_ref', 'all_ref'],  在final answer中加入哪些reference
                'is_fast': True,  # 是否速通模式
                'context_length': 30000,
                'is_answer_when_absent_ref': 'false'
            },
            "FIRST_SENTENCE_CONFIG": 0.995,
            "IAAR_DataBase_Doc": {
                "url": 'xxx',
                "url_topnews": 'xxx',
                "access_key": "xxx",
                "file_database_default_param": {
                    "search_type": ["online"],
                },
                "default_param": {
                    "search_type": ["online"],
                    "online_search": {
                        "max_entries": 12,  # 搜索引擎返回文档数量
                        "cache_switch": True,
                        "baidu_field": {
                            "switch": False,
                            "mode": "relevance",
                            "type": "page"},
                        "bing_field": {
                            "switch": True,
                            "mode": "relevance",
                            "type": "page"
                        },
                        "sogou_field": {
                            "switch": False,
                            "mode": "relevance",
                            "type": "page"}
                    }
                },
                "query_news": ["今天有什么新闻", "本周有什么新闻", "本月有什么新闻"],
                "use_iaar_hot_news": True,
                "is_demo": False,
                "hot_news_count": 50
            },
            "RAG_CONFIG": {
                "similarity_config": {
                    "method": 'rerank-sft-0829',  # base/llm/rerank/rerank_base
                    "is_filter": True,
                    "simi_bar": 0.0,
                    "model_name": '',
                    "top_n": 100
                },
                "parallel": 5,
                "chunk_min_length": 5,
                "max_chunk": 100,
                "raw_ranker": False,
            },
            "WHITE_LIST_CONFIG": {
                "query_answer": {"scheme_id": "1ee5e17f-6c02-4f03-ae49-769e668b3fd3"},
                "doc_answer": {"scheme_id": "c23cdb51-b342-4ae6-a3d9-d89b984c2d1a"},
                "is_use": "true"
            },
            "QUERY_INTENTION_CONFIG": {
                "is_use": False
            },
            "PDF_CHUNK_SPLIT": {
                "url": "xxx",
                "key": "xxx"
            }
        }
        )
