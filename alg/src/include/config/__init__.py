from __future__ import annotations


from include.config.common_config import CommonConfig
from include.config.prompt_config import PromptConfig
from include.config.query_intent_recognition_config import QueryIntentRecognitionConfig
from include.config.rag_qa_config import RagQAConfig
from include.config.module_config import ModuleConfig
from include.config.query_recommend_config import QueryRecommendConfig
from include.config.timeline_config import TimeLineConfig   
from include.config.doc_qa_config import DocQAConfig


CommonConfig = CommonConfig()
PromptConfig = PromptConfig()
QueryIRConfig = QueryIntentRecognitionConfig()
RagQAConfig = RagQAConfig()
QueryReConfig = QueryRecommendConfig()
TimeLineConfig = TimeLineConfig()
DocQAConfig = DocQAConfig()
ModuleConfig = ModuleConfig(RagQAConfig, DocQAConfig, PromptConfig)


