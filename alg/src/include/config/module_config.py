import os
import spacy
from include.config.files_dir import PinyinCity, GeoLite2

class ModuleConfig():
    def __init__(self, RagQAConfig_dict, DocQAConfig_dict, PromptConfig_dict):
        self.PromptConfig_dict = PromptConfig_dict
        self.COT_scheme_id = "27b13816-80ac-4c63-8bbc-3f77bddbd8f8"
        self.use_whitelist = False
        self.followup_question = True     # 是否开启多轮对话的cot
        self.general_cot_model_name = RagQAConfig_dict["TASK_MODEL_CONFIG"]["get_general_mhq"]    # sft14B模型
        self.timeline_cot_model_name = RagQAConfig_dict["TASK_MODEL_CONFIG"]["get_timeline_mhq"]  # sft72B模型
        self.large_model_name = RagQAConfig_dict["TASK_MODEL_CONFIG"]["large_multihop_rewrite"]   # 开源72B
        self.light_model_name = RagQAConfig_dict["TASK_MODEL_CONFIG"]["light_multihop_rewrite"]   # 开源14B

        self.doc_model_name = DocQAConfig_dict["TASK_MODEL_CONFIG"]["multihop_rewrite"]        # 开源14B
        self.doc_light_model_name = DocQAConfig_dict["TASK_MODEL_CONFIG"]["multihop_rewrite"]  # 开源14B
        # self.check_consistency()  # 双模型一致性检查
        self.initialize()
        self.pinyin_city = PinyinCity
        self.geo_lite = GeoLite2
        self.city_names = list(PinyinCity.values())
        self.spacy_nlp = spacy.load("zh_core_web_sm")
        self.doc_query_types = ["综述问题", "具体问题"]
        self.doc_cot_config = self._init_doc_cot_config()
        self.use_web_summary_rewrite_query = False  # 是否开启网页摘要做时间重写任务

    def initialize(self):
        self.init_template()
        # if "gpt" in self.model_name:
        #     self.init_Gpt_template()
        # else:
        #     self.init_QWEN_template()

    def init_template(self):
        self.__dict__.update({
            "Time_Template" : self.PromptConfig_dict["rewrite_time"]["QWEN_input_item"],
            "Loc_Template" : self.PromptConfig_dict["rewrite_loc"]["QWEN_input_item"],
            "Time_Loc_Template" : self.PromptConfig_dict["rewrite_time_loc"]["QWEN_input_item"],
            "Time_Desc_Template" : self.PromptConfig_dict["rewrite_time_desc"]["QWEN_input_item"],
            "Time_extract_Template" : self.PromptConfig_dict["time_extraction"]["QWEN_input_item"],
            "MultiHopQueryTemplate": self.PromptConfig_dict["multi_hop_qa"]["QWEN_input_item"],
            "MultiHopQueryNumThresholdTemplate": self.PromptConfig_dict["multi_hop_qa_num_threshold"]["QWEN_input_item"],
            "MultiHopQueryDialogueNumThresholdTemplate": self.PromptConfig_dict["multihop_with_dialogue_num_threshold"]["QWEN_input_item"],
            "MultiSplitSupplyTemplate": self.PromptConfig_dict["multi_hop_qa_supply"]["QWEN_input_item"],
            "MultiTimelineTemplate": self.PromptConfig_dict["multi_hop_qa_timeline"]["QWEN_input_item"],
            "MultiTimelineNumThresholdTemplate":self.PromptConfig_dict["multi_timeline_num_threshold"]["QWEN_input_item"],
            "CheckTimeLocTemplate": self.PromptConfig_dict["check_time_loc"]["QWEN_input_item"],
            "QueryDependencyTemplate": self.PromptConfig_dict["judge_dependency"]["QWEN_input_item"],

            "JudgeFunCallTemplate": self.PromptConfig_dict["judge_function_call"]["QWEN_input_item"],
            "JudgeStepBackTemplate": self.PromptConfig_dict["judge_stepback"]["QWEN_input_item"],
            "JudgeWeatherTemplate": self.PromptConfig_dict["judge_ask_weather"]["QWEN_input_item"],
            "JudgeNeedRagTemplate": self.PromptConfig_dict["judge_need_rag"]["QWEN_input_item"],
            "ReplenishQueryInfoTemplate": self.PromptConfig_dict["replenish_query_info"]["QWEN_input_item"],
            "DocTextCOTTemplate": self.PromptConfig_dict["DocTextCOTTemplate"]["QWEN_input_item"],
            "DocTitleCOTTemplate": self.PromptConfig_dict["DocTitleCOTTemplate"]["QWEN_input_item"],
            "DocTableFigCOTOneRushTemplate": self.PromptConfig_dict["DocTableFigCOTOneRushTemplate"]["QWEN_input_item"],
            "DocTitleCOTOneRushTemplate": self.PromptConfig_dict["DocTitleCOTOneRushTemplate"]["QWEN_input_item"],
            "DocTextCOTOneRushTemplate": self.PromptConfig_dict["DocTextCOTOneRushTemplate"]["QWEN_input_item"],
            "DocTableFigCOTTemplate": self.PromptConfig_dict["DocTableFigCOTTemplate"]["QWEN_input_item"],
            "TimeRewriteTemplate": self.PromptConfig_dict["time_direct_rewrite"]["QWEN_input_item"],
            "DocQueryClassifyTemplate": self.PromptConfig_dict["class_doc_question_type"]["QWEN_input_item"],
            "TokenNumRewrite":self.PromptConfig_dict["TokenNumRewrite"]["instruction"],
            "TimeInsertTemplate": self.PromptConfig_dict["time_direct_insert"]["QWEN_input_item"]
            })

    def __getitem__(self, key):
        return self.__dict__.get(key, None)
    
    def check_consistency(self):
        if "gpt" in self.model_name and "gpt" in self.light_model_name:
            pass 
        elif "gpt" not in self.model_name and "gpt" not in self.light_model_name:
            pass
        else:
            raise ValueError("RagQAConfig_dict model choices should be consistent between 'get_multi_hop_queries' and 'multihop_rewrite'.")
        
    def _init_doc_cot_config(self):
        obj = MyClass()
        updated_params = obj.add_params(
            doc_cot_method="parallel_call",   # "each_step"  "one_rush" "parallel_call"   "one_rush_shorter_input"
            one_rush_prompt_length=20, 
            parallel_call_bs = 10    # 10 的时候最快
            )
        return updated_params

class Params:
    def __init__(self):
        self.__dict__ = {}

    def add_attribute(self, **kwargs):
        self.__dict__.update(kwargs)
        return self
    
class MyClass:
    def __init__(self):
        # 初始化一个Params对象
        self.params = Params()
    def add_params(self, **kwargs):
        return self.params.add_attribute(**kwargs)
