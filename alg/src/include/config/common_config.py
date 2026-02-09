"""Common" variables."""
import os
import json
from include.config.get_special_user_id import get_special_user_ids


current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "special_user_ids.json")

try:
    get_special_user_ids()
    print("successfully update special_user_ids")
except:
    print("fail to update special_user_ids")


with open(file_path, "r", encoding="utf-8") as file:
    special_user_ids = json.load(file)
special_user_ids_list = [item['_id'] for item in special_user_ids]
special_user_ids_dict = {item['_id']: item for item in special_user_ids}


class CommonConfig:
    def __init__(self, ):
        self.__dict__ = {
            "LOG_CONFIG": {
                "dir": "./log"  # root directory of log
            },
            "AUTH_CONFIG": {
                "key": "xxx"
            },
            "FSCHAT": {
                "vllm_url": "https://apigateway.online.xinyunews.cn/inference_new/fschat/generate",
                "hf_url": "https://apigateway.online.xinyunews.cn/inference_new/fschat/hf_generate",
                "general_url": "https://apigateway.online.xinyunews.cn/inference_new/fschat/general_generate"
            },
            "NER": {
                "keyword_url": "https://xxx", # the address where ner model is deployed
                "Authorization": "xxx" # the authorization key to use ner model
            },
            "WHITE_LIST": {
                "del_url": "https://apigateway.online.xinyunews.cn/whitelist/whitelistmanagement/delete",
                "create_url": "https://apigateway.online.xinyunews.cn/whitelist/whitelistmanagement/create",
                "update_url": "https://apigateway.online.xinyunews.cn/whitelist/whitelistmanagement/update",
                "search_url": "https://apigateway.online.xinyunews.cn/whitelist/whitelistmanagement/search"
            },
            "RERANK": {
                "env": 'local',
                "url": 'https://apigateway.online.xinyunews.cn/inference_new/fschat/general_generate',
                'topk_es': 1000,
                'topk_vec': 500,
                'topk_rerank': 150,
                'limit': 200,
                'cnt_chunk': 50,  # the number of references mounted to each sub-query
                'sim2theme_thread': 0.1,  # similarity threshold, materials which has less similarity score than the value will be eliminated
            },
            "CHUNK_SPLIT": {
                "model": "test_wjj_bge_base_zh_embedding_general",
            },
            "SIMILARITY_CONFIG": {
                "url": "https://apigateway.online.xinyunews.cn/inference_new/fschat/general_generate",
                "baai_sim_general": "baai_sim_general",
                "embedding": "embedding_general",
                "embedding_sim_general": "embedding_sim_general"
            },
            "MODEL_CONFIG": {
                "direct_url": {
                    "memory25_72b": "https://apigateway.online.xinyunews.cn/inference_new/fschat/generate",
                    "memory25_14b_7kcot0905_sft_vllm": "https://apigateway.online.xinyunews.cn/inference_new/fschat/generate",
                    "memory_post_mount_qwen15_4b_sft": "https://apigateway.online.xinyunews.cn/inference_new/fschat/generate",
                    "memory25_14b": "https://apigateway.online.xinyunews.cn/inference_new/fschat/generate",
                    "memory_72b_0807sft_vllm": "https://apigateway.online.xinyunews.cn/inference_new/fschat/generate",
                },
                "stream_url": {
                    "memory25_72b": "https://apigateway.online.xinyunews.cn/inference_new/fschat/stream_generate",
                    "memory25_14b_7kcot0905_sft_vllm": "https://apigateway.online.xinyunews.cn/inference_new/fschat/stream_generate",
                    "memory_post_mount_qwen15_4b_sft": "https://apigateway.online.xinyunews.cn/inference_new/fschat/stream_generate",
                    "memory25_14b": "https://apigateway.online.xinyunews.cn/inference_new/fschat/stream_generate",
                    "memory_72b_0807sft_vllm": "https://apigateway.online.xinyunews.cn/inference_new/fschat/stream_generate"
                },
                "retry_time": 5,
                "qwen2_72b_vllm": {"forward_request": False, "index": "qwen2_72b_vllm",
                                   "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"},
                "qwen25_14b_vllm": {"forward_request": False, "index": "qwen25_14b_vllm",
                                    "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"},
                "memory25_72b": {"forward_request": False,
                                 "index": "qwen25_72b_int4_vllm",
                                 "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"},
                "memory_post_mount_qwen15_4b_sft": {"forward_request": False,
                                                    "index": "post_mount_qwen15_4b_sft",
                                                    "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"},
                "memory25_14b": {"forward_request": False,
                                 "index": "qwen25_14b_instruct_vllm",
                                 "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"},
                "memory_72b_0807sft_vllm": {"forward_request": False,
                                 "index": "qwen2_72b_0807sft_vllm",
                                 "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"},
                "memory25_14b_7kcot0905_sft_vllm": {"forward_request": False,
                                 "index": "memory25_14b_7kcot0905_sft_vllm",
                                 "prompt_template": "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"}

            },
            "ES_QA": {
                "url": "http://xxx.xxx.xxx.xxx:xxxx", # replace it with your own elastic search server address
                "elastic": "password", # replace it with your own username to log into elasticsearch, the default username is "elastic"
            },
            "MILVUS": {
                "uri": "http://xxx.xxx.xxx.xxx:xxxx", # the address and port where milvus is deployed
                "username": "username", # replace it with your own username to log into milvus
                "password": "password", # replace it with your own password to log into milvus
            },
            "XINHUA": {
                "app_id": "",
                "access_key": "",
                "url": "",
                "vector_db_url": "",
                "search_news_es_url": "h"
            },
            "IAAR_DataBase": {
                "url": 'https://apigateway.online.xinyunews.cn/database/api/atlas/detail/search',
                "summary_url": 'https://apigateway.online.xinyunews.cn/database/api/atlas/summary/search',
                "url_topnews": 'https://apigateway.online.xinyunews.cn/database/api/atlas/topnews/search',
                "access_key": "xxx",
                "default_param": {
                    "search_type": ["online"],
                    "online_search": {
                        "max_entries": 12,  # the number of documents returned by the search engine
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
                "default_param_pro_flag": {
                    "return_num": 12,
                    "baidu_field": {
                        "switch": False,
                        "type": "page"
                    },
                    "bing_field": {
                        "switch": True,
                        "type": "page"
                    },
                    "sogou_field": {
                        "switch": False,
                        "type": "page"
                    }
                },
                "use_iaar_hot_news": True,
                "is_demo": False,
                "hot_news_count": 50
            },
            "SW_CONFIGS": {
                "disable": "true",
                "server_url": "xxx",
                "service_name": "service-sw",
                "instance_name": "instance-sw",
            },
            "PDF_PROCESS_CONFIGS": {
                "multimodal_url": "",
                "multimodal_disable": "",
                "pdf_extract_url": "",
                "pdf_extract_mode": ""
            },
        }

    def __getitem__(self, key):
        return self.__dict__.get(key, None)
