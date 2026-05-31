"""Common" variables."""
from include.config.prompt_template import *


class PromptConfig:
    def __init__(self, ):
        self.__dict__ = {
            "basic_abstract_task": {
                "task_desc": "基础摘要任务",
                "temp_id": "task_00000001",
                "instruction": "【生成任务：文本摘要】我要你担任新闻编辑。我将为您提供与新闻相关的故事或主题，"
                               "您将撰写一篇摘要，对手头的主题提供有见地的总结。您应该利用自己的经验，深思熟虑地总结重要的事情，"
                               "用事实支持主张，努力将文本概括清晰且完整。\n请对以下文本进行摘要。\n\n",
                "input_item": "{all_content}\n\n摘要结果需满足以下要求：\n1.字数为{write_len}个字左右；"
                              "\n2.符合{write_style}文章风格；\n3.包含原始文本必要关键信息，内容全面准确，"
                              "结构清晰，主题突出，客观公正，完全依据事实，没有加入个人观念或对事实的修改。"
                              "\n【附加信息】摘要文本所在文章的标题是【{page_title}】",
            },
            "multi_hop_qa": {
                "task_desc": "多跳问答任务",
                "temp_id": "task_00000002",
                "instruction": "",
                "GPT_input_item": MultiHopQuery_QWEN,
                "QWEN_input_item": MultiHopQuery_QWEN,
            },
            "retrival_range": {
                "task_desc": "关键实体抽取任务",
                "temp_id": "task_00000003",
                "instruction": "",
                "input_item": "请从问题中提取关键的人物、地点、关键词信息，并给出为了回答该问题，应该从什么时间到什么时间检索参考材料,"
                              "请以json的形式回答，如果无法推断相关信息，请返回空字符串。\n问题：{question}"
                              "\n 答案格式为: {{\"人物\": [\"XXX\"], \"地点\": [\"XXX\"], \"关键词\": [\"XXX\", \"XXX\"], "
                              "\"材料开始时间\": \"yyyy-mm-dd\", \"材料结束时间\": \"yyyy-mm-dd\"}}, 如: {{\"人物\": [\"小明\"],"
                              " \"地点\": [], \"关键词\": [], \"材料开始时间\": \"2022-11-06\", \"材料结束时间\": \"2022-12-20\"}}，"
                              "请直接输出一个json，不要附加额外说明或符号。",
            },
            "query_answer": {
                "task_desc": "问答任务base版--有子问答",
                "temp_id": "task_00000004",
                "instruction": QueryAnswerTemplate
            },
            "query_answer_quickpass": {
                "task_desc": "问答任务快速版--有子问答",
                "temp_id": "task_00000004",
                "instruction": QueryAnswerQuickpassTemplate
            },
            "query_simple_answer": {
                "task_desc": "简单问答任务",
                "temp_id": "task_00000004",
                "instruction": SubQueryAnswerTemplate
            },
            "query_simple_answer_non_pro": {
                "task_desc": "简单问答任务-non-pro版",
                "temp_id": "task_00000030",
                "instruction": SubQueryAnswerNonProTemplate
            },
            # "chain-mid": {
            #     "task_desc": "思维链问答任务",
            #     "temp_id": "task_00000004",
            #     "instruction": SubQueryAnswerTemplate
            # },
            # "chain-final": {
            #     "task_desc": "问答任务base版",
            #     "temp_id": "task_00000004",
            #     "instruction": QueryAnswerTemplate
            # },
            "query_reject": {
                "task_desc": "问题拒答",
                "temp_id": "task_00000007",
                "instruction": QueryRejectTemplate},

            "query_keyword": {
                "task_desc": "问题关键词提取",
                "temp_id": "task_00000008",
                "instruction": QueryKeywordTemplate
            },
            "query_supply": {
                "task_desc": "问题补充",
                "temp_id": "task_00000009",
                "instruction": QuerySupplyTemplate
            },
            "query_reinforce": {
                "task_desc": "问题增强",
                "temp_id": "task_000000010",
                "instruction": QueryReinforceTemplate
            },
            "quick_query_reinforce": {
                "task_desc": "问题增强",
                "temp_id": "task_000000010",
                "instruction": QuickQueryReinforceTemplate
            },
            "multi_hop_qa_supply": {
                "task_desc": "带supply信息的多跳问答任务",
                "temp_id": "task_00000001",
                "instruction": "",
                "GPT_input_item": MultiSplitSupplyTemplate_QWEN,
                "QWEN_input_item": MultiSplitSupplyTemplate_QWEN
            },
            "multi_hop_qa_num_threshold": {
                "task_desc": "限制拆分条数的COT",
                "temp_id": "task_00000001",
                "instruction": "",
                "GPT_input_item": MultiHopQueryNumThreshold_QWEN,
                "QWEN_input_item": MultiHopQueryNumThreshold_QWEN
            },
            "multihop_with_dialogue_num_threshold": {
                "task_desc": "多轮对话限制拆分条数的COT",
                "temp_id": "task_00000001",
                "instruction": "",
                "GPT_input_item": MultiHopQuery_WithDialogue_NumThreshold,
                "QWEN_input_item": MultiHopQuery_WithDialogue_NumThreshold
            },
            "multi_hop_qa_timeline": {
                "task_desc": "脉络梳理的多跳问答任务",
                "temp_id": "task_00000004",
                "instruction": "",
                "GPT_input_item": MultiTimelineTemplate_QWEN,
                "QWEN_input_item": MultiTimelineTemplate_QWEN,
            },
            "multi_timeline_num_threshold": {
                "task_desc": "脉络梳理的多跳问答任务且有拆分个数要求",
                "temp_id": "task_00000004",
                "instruction": "",
                "GPT_input_item": MultiTimelineSplitNumThreshold_QWEN,
                "QWEN_input_item": MultiTimelineSplitNumThreshold_QWEN,
            },
            "replenish_query_info": {
                "task_desc": "query信息补全任务",
                "temp_id": "task_00000004",
                "instruction": "",
                "GPT_input_item": ReplenishQueryInfoTemplate,
                "QWEN_input_item": ReplenishQueryInfoTemplate,
            },
            "judge_dependency": {
                "task_desc": "判定问题之间依赖性的任务",
                "temp_id": "task_00000002",
                "instruction": "",
                "GPT_input_item": QueryDependencyTemplate_QWEN,
                "QWEN_input_item": QueryDependencyTemplate_QWEN,
            },
            "check_time_loc": {
                "task_desc": "检查时间地点需求的任务",
                "temp_id": "task_00000003",
                "instruction": "",
                "GPT_input_item": CheckTimeLocTemplate_GPT,
                "QWEN_input_item": CheckTimeLocTemplate_QWEN,
            },
            "rewrite_time": {
                "task_desc": "时间信息重写功能",
                "temp_id": "task_00000005",
                "instruction": "",
                "GPT_input_item": "已知提问时间'{0}'，提问问题：'{1}'。\n请整理信息并输出一个时间信息充分的问题，注意只输出问题内容即可：",
                "QWEN_input_item": "请根据问题素材补充提供的时间，整理信息并输出一个时间信息充分的问题，注意：只输出问题内容即可，且尽量只插入时间信息、减少对原问题的改写。\n举例如下：\n问题素材：天气怎么样？补充时间：1月1日\n回答：1月1日的天气怎么样？\n\n提问如下：\n问题素材：'{1}'，补充时间：'{0}'\n回答：",
            },
            "rewrite_loc": {
                "task_desc": "地点信息重写功能",
                "temp_id": "task_00000006",
                "instruction": "",
                "GPT_input_item": "已知提问地点'{0}'，提问问题：'{1}'。\n请整理信息并输出一个地点信息充分的问题，注意只输出问题内容即可：",
                "QWEN_input_item": "请根据问题素材补充提供的地点，整理信息并输出一个地点信息充分的问题，注意：只输出问题内容即可，且尽量只插入地点信息、减少对原问题的改写。\n举例如下：\n问题素材：当地有什么活动？，补充地点：上海\n回答：上海有什么活动？\n\n提问如下：\n问题素材：'{1}'，补充地点：'{0}'\n回答：",
            },
            "rewrite_time_loc": {
                "task_desc": "时间地点信息重写功能",
                "temp_id": "task_00000007",
                "instruction": "",
                "GPT_input_item": "已知提问时间'{0}'，提问地点'{1}'，提问问题：'{2}'。\n请整理信息并输出一个时间地点信息充分的问题，注意只输出问题内容即可：",
                "QWEN_input_item": "请根据问题素材补充提供的时间和地点，整理信息并输出一个时间地点信息充分的问题，注意只输出问题内容即可，且尽量只插入时间或地点信息、减少对原问题的改写。\n举例如下：\n问题素材：天气怎么样？补充时间：1月1日，补充地点：上海\n回答：1月1日上海的天气怎么样？\n\n提问如下：\n问题素材：'{2}'，补充时间：'{0}'，补充地点：'{1}'\n回答：",
            },
            "rewrite_time_desc": {
                "task_desc": "时间地点信息重写功能",
                "temp_id": "task_00000007",
                "instruction": "",
                "GPT_input_item": "我是一个8岁的学生，请帮我通过时间描述来计算准确的时间点或者时间段。\n注意：1.直接告诉我答案。2.精准程度与时间描述保持一致(如果描述为'年'，具体到'年'即可；如果描述为'月'，具体到'月'即可；如果描述为'季度'，具体到'月'即可；如果描述为'周'，具体到'周'即可；如果描述为'中旬'、'以来'、'期间'，则保留原本描述)。3.注意描述的是时间段还是时间点，如果有“以来”、“期间”等描述表示时间段。4.不要打印思维过程。\n\n当前时间是'{0}'，时间描述是'{1}'，那么指向的时间或时间段是什么？请直接输出答案，不要输出其他内容！",
                "QWEN_input_item": "我是一个8岁的学生，请帮我通过时间描述来计算准确的时间点或者时间段。\n注意：1.直接告诉我答案。2.精准程度与时间描述保持一致(如果描述为'年'，具体到'年'即可；如果描述为'月'，具体到'月'即可；如果描述为'季度'，具体到'月'即可；如果描述为'周'，具体到'周'即可；如果描述为'中旬'、'以来'、'期间'，则保留原本描述)。3.注意描述的是时间段还是时间点，如果有“以来”、“期间”等描述表示时间段。4.不要打印思维过程。\n\n当前时间是'{0}'，时间描述是'{1}'，那么指向的时间或时间段是什么？请直接输出答案，不要输出其他内容！"
            },
            "time_extraction": {
                "task_desc": "query时间抽取",
                "temp_id": "task_00000008",
                "instruction": "",
                "GPT_input_item": "请从下面的句子中提取关于时间描述的词语，比如：今天、明天、上周、本月、去年、上个季度、五年前等等。注意:1.除了抽取的词语，不要返回其他任何文字。2.如果遇到类似“上周周三”这样的描述直接返回“上周周三”，而不是拆分成“上周”“周三”分开返回。3.不要抽取模糊的时间描述词，比如：最近（请区分‘最近’和‘最近一个月’这种描述，前者不抽取，后者需要抽取）、这段时间、近期、未来、前段时间等等，不对这些词语做抽取。4. 如果可以抽取时间描述词，仅返回一个词语，不要该词语前后的冗余部分）。5.不要抽取行业产品和服务中的时间描述词汇，一般表示有效期、服务期限或某个特定时间段的服务，例如：银行产品描述词（三年期定存、1年基金投资、10年期）、电信行业产品描述词（两年保修、一年换新等）、医疗类产品描述词（三年医疗保险、1年健康检测）等等，这种情况返回None表示不抽取。6.抽取的时间描述词一定是在句子中含有的，如果没有时间描述词，返回None\n{0}",
                "QWEN_input_item": "请从提供的句子素材中提取关于时间描述的词语，常用时间描述词的列表如下：[一个月之内, 一周之内, 一周后, 一年之内, 1年之内, 3个月之内, 3个月前, 三个月之内, 三个月前, 三个月后, 三周前, 三年前, 上个暑假, 上个月, 上半年, 上半月, 上周, 下个月, 下半年, 下半月, 下月初, 下月末, 五年前, 五年后, 今天, 今年, 今年年初, 今年年底, 前一周, 前天, 前年, 十年, 十年前, 十年来, 去年, 去年年初, 去年年底, 后天, 大前年, 大后天, 往后推五年, 接下来七天, 接下来的一周, 明天, 明年, 明年年初, 明年年底, 昨天, 未来一个月, 未来一年, 未来七天, 未来三个月, 未来两周, 未来两年, 未来十天, 未来十年, 未来的一个月, 未来的一周, 未来的一年, 本周, 本月, 本月中旬, 本月底, 过去两周, 过去的一个月, 过去的一周, 过去的一年, 近10年, 近5年, 近3年, 近1年, 近三年, 近两个月, 近十年, 这个月]，请根据提供的常用时间描述词抽取描述非常相近的词语。\n\n注意:\n1.除了抽取的词语，不要返回其他任何文字。\n2.如果某个时间词语前后有其他具体的时间词语（比如年份、月份等），则不抽取返回并None，例如：2022年上半年、2024年第三季度、8月下半月等等。\n3.不要抽取模糊的时间描述词，比如：最近（请区分‘最近’和‘最近一个月’这种描述，前者不抽取，后者需要抽取）、这段时间、近期、未来、前段时间等等，不对这些词语做抽取。\n4.如果可以抽取时间描述词，仅返回一个词语，不要该词语前后的冗余部分）。\n5.不要抽取行业产品和服务中的时间描述词汇，一般表示有效期、服务期限或某个特定时间段的服务，例如：银行产品描述词（如：三年期定存、1年基金投资、10年期）、电信行业产品描述词（如：两年保修、一年换新）、医疗类产品描述词（如：三年医疗保险、1年健康检测）、财报类描述词（如：第一季度财报、上半年财报）等等，这种情况返回None表示不抽取。\n6.抽取的时间描述词一定是在句子中含有的，如果没有时间描述词，返回None\n\n句子素材：{0}",
            },
            "time_direct_rewrite":{
                "task_desc": "直接对query做时间重写",
                "temp_id": "task_00000008",
                "instruction": "",
                "GPT_input_item": TimeRewriteTemplate,
                "QWEN_input_item": TimeRewriteTemplate  
            },
            "time_direct_insert":{
                "task_desc": "直接对query做时间嵌入判断",
                "temp_id": "task_00000008",
                "instruction": "",
                "GPT_input_item": TimeInsertTemplate,
                "QWEN_input_item": TimeInsertTemplate  
            },
            "judge_need_rag": {
                "task_desc": "检索需求判定任务",
                "temp_id": "task_000000012",
                "instruction": "",
                "GPT_input_item": JudgeNeedRag_QWEN,
                "QWEN_input_item": JudgeNeedRag_QWEN,
            },
            "judge_function_call": {
                "task_desc": "Tool调用需求判定",
                "temp_id": "task_00000001",
                "instruction": "",
                "GPT_input_item": JudgeFunCallTemplate_QWEN,
                "QWEN_input_item": JudgeFunCallTemplate_QWEN,
            },
            "judge_stepback": {
                "task_desc": "回退判定和改写",
                "temp_id": "task_00000002",
                "instruction": "",
                "GPT_input_item": JudgeStepBackTemplate_QWEN,
                "QWEN_input_item": JudgeStepBackTemplate_QWEN,
            },
            "judge_ask_weather": {
                "task_desc": "判定询问天气",
                "temp_id": "task_00000003",
                "instruction": "",
                "GPT_input_item": JudgeWeatherTemplate_QWEN,
                "QWEN_input_item": JudgeWeatherTemplate_QWEN,
            },
            "query_translate": {
                "task_desc": "全英问题翻译",
                "temp_id": "task_000000013",
                "instruction": QueryTranslateTemplate,
            },
            "queryfur_rec": {
                "task_desc": "追问问题",
                "temp_id": "task_000000014",
                "QWEN_input_item": QueryFurRecTemplate_QWEN
            },
            "timeline_query_rewrite": {
                "task_desc": "问题改写为时间线问题",
                "temp_id": "task_00000004",
                "instruction": "",
                "GPT_input_item": TimelineQueryRewriteTemplate_GPT,
                "QWEN_input_item": TimelineQueryRewriteTemplate_QWEN,
            },
            "timeline_event_extract": {
                "task_desc": "事件抽取",
                "temp_id": "task_00000025",
                "instruction": "",
                "example": TimelineEventExtractExampleTemplate_GPT,
                "GPT_input_item": TimelineEventExtractTemplate_GPT,
                "QWEN_input_item": TimelineEventExtract_QWEN
            },
            "timeline_highlight_extract_without_granularity": {
                "task_desc": "时间线highlight提取",
                "temp_id": "task_00000005",
                "instruction": "",
                "GPT_input_item": TimelineHighlightExtractWithoutGranularityTemplate_GPT,
                "QWEN_input_item": TimelineHighlightExtractWithoutGranularityTemplate_QWEN,
            },
            "queryDocCorrelation": {
                "task_desc": "query与doc的关联度判断",
                "temp_id": "task_00000012",
                "instruction": QueryDocCorTemplate
            },
            "timeline_granularity": {
                "task_desc": "时间线粒度提取",
                "temp_id": "task_00000006",
                "instruction": "",
                "GPT_input_item": TimelineGranularityTemplate_GPT,
                "QWEN_input_item": TimelineGranularityTemplate_QWEN,
            },
            "useful_reference": {
                "task_desc": "检索材料相关有用性判断",
                "temp_id": "task_00000025",
                "instruction": UsefulReferenceTemplate
            },
            "general_query_answer": {
                "task_desc": "通用问题回答（不带引证标识）",
                "temp_id": "task_00000026",
                "instruction": GeneralQueryAnswerTemplate
            },
            "retrival_range_new": {
                "task_desc": "问题检索范围抽取（新版）",
                "temp_id": "task_00000015",
                "instruction": QueryRetrievalRangeNewTemplate
            },
            "hot_events_related_query_s1": {
                "task_desc": "判断用户输入是否与强时效性新闻事件相关",
                "temp_id": "task_00000028",
                "instruction": HotEventRelatedQueryS1Template
            },
            "hot_events_related_query_s2": {
                "task_desc": "基于检索判断用户输入是否与某一特定事件相关联",
                "temp_id": "task_00000029",
                "instruction": HotEventRelatedQueryS2Template
            },
            "add_reference_to_answer": {
                "task_desc": "后挂载（新版）",
                "temp_id": "task_00000016",
                "instruction": AddReferenceToAnswerTemplate
            },
            "query_answer_multi_round": {
                "task_desc": "问答任务多轮对话版--多轮问答前缀",
                "temp_id": "task_00000027",
                "instruction": QueryAnswerMultiRoundTemplate
            },
            "class_doc_question_type":{
                "task_desc": "docquery2类问题分类",
                "temp_id": "task_00000098",
                "instruction": "",
                "GPT_input_item": "请对我提出的问题的性质做分类，大致为两个类别：综述问题、具体问题。\n问题：{0}\n分类：",
                "QWEN_input_item":"请对我提出的问题的性质做分类，大致为两个类别：综述问题、具体问题\n<综述问题>涉及的特点说明：\n1. 宏观视角：是关于整个报告的总体概览，关注的是报告的整体框架、核心观点或主要结论。\n2. 广泛性：这类问题通常覆盖了报告中涉及的多个方面，而不是聚焦于某个细节。\n3. 战略意义：该类问题有助于理解报告的战略导向，比如行业趋势、市场定位等。\n4. 批判性思考：鼓励对报告整体的逻辑性、数据支持度等方面进行评价。\n<综述问题>示例：\n1. 这份研报的主要结论是什么？\n2. 报告对于我们的投资策略有何启示？\n3. 请仔细阅读这篇宏观研究报告，并写一篇总结。\n\n<具体问题>涉及的特点说明：\n1. 细节关注：针对报告中某一特定部分或数据点的深入探讨。\n2. 精确性：这类问题要求提供准确的数据、事实或分析结果。\n3. 实证依据：通常需要报告中的具体证据来回答，如财务比率、市场增长率等。\n4. 操作指导：可能直接关系到具体的交易决策或投资建议。\n<具体问题>示例：\n1. 报告是如何计算出未来五年该行业的复合年增长率的？\n2. 报告中提到了哪些竞争对手，它们的市场份额变化如何？\n3. 根据报告，最近的政策变动对行业的影响是什么？\n\n要求：\n直接回答类别名称，不要打印解释和备注。\n只能选择一个类别，当一个问题涉及到两种类别时，选择比重更大的那一类。\n\n问题：{0}\n分类："
            },
            "DocTextCOTTemplate": {
                "task_desc": "文档文本COT",
                "temp_id": "task_000000012",
                "instruction": "",
                "QWEN_input_item": DocTextCOTTemplate,
            },
            "DocTitleCOTOneRushTemplate": {
                "task_desc": "文档文本COT一把出",
                "temp_id": "task_000000012",
                "instruction": "",
                "QWEN_input_item": DocTitleCOTOneRushTemplate,
            },
            "DocTextCOTOneRushTemplate": {
                "task_desc": "文档文本COT一把出",
                "temp_id": "task_000000012",
                "instruction": "",
                "QWEN_input_item": DocTextCOTOneRushTemplate,
            },
            "DocTableFigCOTOneRushTemplate": {
                "task_desc": "文档文本COT一把出",
                "temp_id": "task_000000012",
                "instruction": "",
                "QWEN_input_item": DocTableFigCOTOneRushTemplate,
            },
            "DocTitleCOTTemplate": {
                "task_desc": "文档标题COT",
                "temp_id": "task_000000012",
                "instruction": "",
                "QWEN_input_item": DocTitleCOTTemplate,
            },
            "DocTableFigCOTTemplate": {
                "task_desc": "文档图表COT",
                "temp_id": "task_000000012",
                "instruction": "",
                "QWEN_input_item": DocTableFigCOTTemplate,
            },
            "DocAnswerMix": {
                "task_desc": "文档问答速通版",
                "temp_id": "task_000000012",
                "instruction": DocAnswerMixTemplate
            },
            "DocAnswerMix_SubAnswer": {
                "task_desc": "文档问答子问题回答",
                "temp_id": "task_000000012",
                "instruction": DocAnswerMix_SubAnswerTemplate
            },
            "DocAnswerMix_FinalAnswer": {
                "task_desc": "文档问答终问题回答",
                "temp_id": "task_000000012",
                "instruction": DocAnswerMix_FinalAnswerTemplate
            },
            "DocAnswerMixWithExample": {
                "task_desc": "文档图表COT-带示例",
                "temp_id": "task_000000013",
                "instruction": DocAnswerMixWithExampleTemplate
            },
            "TokenNumRewrite": {
                "task_desc": "对字数要求的query做兑换重写",
                "temp_id": "task_000000013",
                "instruction": "你是一名人工智能助理，使用思维链（CoT）方法和反思来回答询问。请分析我输入的query，如果query问题中有对于回答字数的要求，则做一些计算兑换，比例为1:0.6，对query重新修改并输出修改后的query；如果没有对于回答字数的要求，则返回‘无需修改’。遵循以下步骤返回你的回答：\n1.在标签中逐步思考问题：<thinking>思考过程</thinking>。\n2.在标签中提供你最终、简洁的答案：<output>最终答案</output>。\n\n举例如下：\nquery：2022年上半年房地产交易增长因素分析\n回答：<thinking>首先，分析query，这里并没有明确提到字数的要求，因此不需要做字数上的计算兑换。</thinking>\n<output>无需修改</output>\n\nquery：假设你是著名的首席宏观经济分析师，请你仔细阅读这篇宏观研究报告，并写一篇1000字左右的总结。\n回答：<thinking>需要根据给定的比例1:0.6计算实际需要撰写的字数。1000字按照这个比例计算，实际需要撰写600字左右的总结。</thinking>\n<output>假设你是著名的首席宏观经济分析师，请你仔细阅读这篇宏观研究报告，并写一篇600字左右的总结。</output>\n\nquery：{0}\n回答："
            }
        }

    def __getitem__(self, key):
        return self.__dict__.get(key, None)
