from .common_config import CommonConfig


class QueryRecommendConfig(CommonConfig):
    def __init__(self):
        super().__init__()
        self.__dict__.update({
            "QUERYRECDB": {
                "ES": {
                    "url": "http://xxx.xxx.xxx.xxx:xxxx", # the address and port where elastic search is deployed
                    "auth": ('default', 'password'), # replace them with your own username and password to log into milvus
                    "index_name": "news_questions"
                },
                "MV": {
                    "url": "http://xxx.xxx.xxx.xxx:xxxx", # the address and port where milvus is deployed
                    "auth": ("username", "password"), # replace them with your own username and password to log into milvus
                    "collection_name": "ainews_questions_test"
                },
                "Recall":{
                    "use_channel": "es",
                    "search_type": "query_string"
                    },
                "Ranking":{
                    "ranking_weight": {"score": 1, "hit_frequency": 0.1, "pub_time": 1},
                    "field": "query",
                    "use_channel": "es",
                    "diversity_ranking": "field",
                    "similarity_threshold": 0.4
                },
                "QuestionMainPage":{
                    "ranking_weight": {"score": 0.0, "hit_frequency": 0.5, "pub_time": 0.5},
                    "field": "query",
                    "use_channel": "es",
                    "diversity_ranking": "field"
                }
                
            },
            "QUERYRECMODEL": {
                "query_fur_rec": "memory25_14b",
                "answer_len": 256
            },
            "WHITE_LIST_CONFIG": {
                "query_recommend": "e26084f0-941f-4a79-bcaa-1635b4e3b025",
                "further_question_recommend": "de91e727-a5ce-45c5-b087-0c298bfd49f9"
            }
        }
        )
