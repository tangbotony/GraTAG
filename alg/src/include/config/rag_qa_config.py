from .common_config import CommonConfig


class RagQAConfig(CommonConfig):
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
                "url": "https://cloud.infini-ai.com/AIStudio/inference/api/if-dampiq5krmbeyqec/insert_images",
                "url_duplicate": "https://cloud.infini-ai.com/AIStudio/inference/api/if-dampiq5krmbeyqec/images_filtering_url_mp",
                'token': "xxx",
                "bucket_name": "public-crawler",
                "is_limit_candidate_image": "true",
                "limit_candidate_image_size": 60,
            },
            # 任务对应模型名作为llm_caller_utils.get_llm_call_func【model_name】参数传入，需确保有对应函数路由
            "TASK_MODEL_CONFIG": {
                'query_abstract': "memory25_14b",  # 文本摘要
                "question_supplement": "memory_72b_0807sft_vllm",  # 问题补充
                "question_reinforce": "memory25_14b",  # 问题增强
                "question_keyword": "memory_72b_0807sft_vllm",  # 问题关键词生成
                "generate_answer": "memory25_72b",  # 最终答案生成
                "generate_answer_pro_flag": "memory25_72b",  # 最终答案生成
                "generate_sub_answer": "memory25_72b",  # 子问题答案生成
                "retrival_range": "memory25_72b",  # 问题关键信息提取
                "retrival_range_pro_flag": "memory25_14b",  # 问题关键信息提取
                "get_question_supplement": "memory_72b_0807sft_vllm",  # 问题补充
                "large_multihop_rewrite": "memory25_72b",                   # 临时使用，多轮对话cot
                "light_multihop_rewrite": "memory25_14b",                   # 时间改写
                "get_general_mhq": "memory25_14b_7kcot0905_sft_vllm",  # general 思维链
                "get_timeline_mhq": "memory_72b_0807sft_vllm",              # timeline 思维链
                "useful_reference": "memory25_72b",  # 行程类问题相关性判断
                "general_query_answer": "memory25_72b",  # 行程类问题问答
                "add_reference_to_answer": "memory_post_mount_qwen15_4b_sft"
            },
            "RAG_CONFIG": {
                "similarity_config": {
                    "method": 'rerank-sft-0829',  # base/llm/rerank/rerank_base
                    "is_filter": True,
                    "simi_bar": 0.8,
                    "model_name": 'gpt-4o',
                    "top_n": 30
                },
                "parallel": 10,
                "chunk_min_length": 20,
                "max_chunk": 60,
                "raw_ranker": True,
            },
            "EXP_CONFIG": {
                'add_fig': "true",  # 是否在答案中调用图片
                'is_retrieval_range': "true",  # 是否采用retrieval range过滤reference
                'is_reinforce': "false",  # 是否采用问题增强
                'recall_rag': 'without_upstream',  # ['with_upstream', 'without_upstream']  是否在思维链下游子问题检索时拼接上游问题检索词
                'add_ref_to_final_answer_mode': 'all_ref',  # ['no_ref', 'ori_query_ref', 'all_ref'],  在final answer中加入哪些reference
                'is_fast': 'true',  # 是否速通模式
                'context_length': 20000,
                'is_answer_when_absent_ref': 'false'
            },
            "FIRST_SENTENCE_CONFIG": 0.90,
            "WHITE_LIST_CONFIG": {
                "query_answer": {"scheme_id": "1ee5e17f-6c02-4f03-ae49-769e668b3fd3"},
                "is_use": "true"
            }
        }
        )
