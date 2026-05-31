import os

cur_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(cur_dir, "QueryKeyword.txt"), "r", encoding="utf8") as f:
    QueryKeywordTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryReinforce.txt"), "r", encoding="utf8") as f:
    QueryReinforceTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QuickQueryReinforce.txt"), "r", encoding="utf8") as f:
    QuickQueryReinforceTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QuerySupply.txt"), "r", encoding="utf8") as f:
    QuerySupplyTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "CheckTimeLocation_QWEN.txt"), "r", encoding="utf8") as f:
    CheckTimeLocTemplate_QWEN = "".join(f.readlines())
with open(os.path.join(cur_dir, "CheckTimeLocation_GPT.txt"), "r", encoding="utf8") as f:
    CheckTimeLocTemplate_GPT = "".join(f.readlines())

with open(os.path.join(cur_dir, "JudgeNeedRag_QWEN.txt"), "r", encoding="utf8") as f:
    JudgeNeedRag_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "MultiHopQuery_QWEN.txt"), "r", encoding="utf8") as f:
    MultiHopQuery_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "MultiSplitSupply_QWEN.txt"), "r", encoding="utf8") as f:
    MultiSplitSupplyTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "MultiTimelineSplit_QWEN.txt"), "r", encoding="utf8") as f:
    MultiTimelineTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "MultiTimelineSplitNumThreshold_QWEN.txt"), "r", encoding="utf8") as f:
    MultiTimelineSplitNumThreshold_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "MultiHopQueryNumThreshold_QWEN.txt"), "r", encoding="utf8") as f:
    MultiHopQueryNumThreshold_QWEN = "".join(f.readlines())
    
with open(os.path.join(cur_dir, "MultiHopQuery_WithDialogue_NumThreshold.txt"), "r", encoding="utf8") as f:
    MultiHopQuery_WithDialogue_NumThreshold = "".join(f.readlines())

with open(os.path.join(cur_dir, "ReplenishQueryInfoTemplate.txt"), "r", encoding="utf8") as f:
    ReplenishQueryInfoTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryDependency_QWEN.txt"), "r", encoding="utf8") as f:
    QueryDependencyTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "JudgeFunctionCall_QWEN.txt"), "r", encoding="utf8") as f:
    JudgeFunCallTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "JudgeStepBack_QWEN.txt"), "r", encoding="utf8") as f:
    JudgeStepBackTemplate_QWEN = "".join(f.readlines())


with open(os.path.join(cur_dir, "JudgeWeatherQuery_QWEN.txt"), "r", encoding="utf8") as f:
    JudgeWeatherTemplate_QWEN = "".join(f.readlines())
with open(os.path.join(cur_dir, "QueryReject.txt"), "r", encoding="utf8") as f:
    QueryRejectTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "SubQueryAnswer.txt"), "r", encoding="utf8") as f:
    SubQueryAnswerTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "SubQueryAnswerNonPro.txt"), "r", encoding="utf8") as f:
    SubQueryAnswerNonProTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryAnswer.txt"), "r", encoding="utf8") as f:
    QueryAnswerTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryAnswerQuickpass.txt"), "r", encoding="utf8") as f:
    QueryAnswerQuickpassTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryTranslate.txt"), "r", encoding="utf8") as f:
    QueryTranslateTemplate = "".join(f.readlines())
    
with open(os.path.join(cur_dir, "QueryFurRec_QWEN.txt"), "r", encoding="utf8") as f:
    QueryFurRecTemplate_QWEN = "".join(f.readlines())
    
with open(os.path.join(cur_dir, "TimelineRewriteQuery_GPT.txt"), "r", encoding="utf8") as f:
    TimelineQueryRewriteTemplate_GPT = "".join(f.readlines())


with open(os.path.join(cur_dir, "TimelineRewriteQuery_QWEN.txt"), "r", encoding="utf8") as f:
    TimelineQueryRewriteTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimelineHighlightExtractWithoutGranularity_GPT.txt"), "r", encoding="utf8") as f:
    TimelineHighlightExtractWithoutGranularityTemplate_GPT = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimelineHighlightExtractWithoutGranularity_QWEN.txt"), "r", encoding="utf8") as f:
    TimelineHighlightExtractWithoutGranularityTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimelineEventExtract_GPT.txt"), "r", encoding="utf8") as f:
    TimelineEventExtractTemplate_GPT = "".join(f.readlines())
    
with open(os.path.join(cur_dir, "TimelineEventExtract_QWEN.txt"), "r", encoding="utf8") as f:
    TimelineEventExtract_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimelineEventExtractExample_GPT.txt"), "r", encoding="utf8") as f:
    TimelineEventExtractExampleTemplate_GPT = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimelineGranularity_GPT.txt"), "r", encoding="utf8") as f:
    TimelineGranularityTemplate_GPT = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimelineGranularity_QWEN.txt"), "r", encoding="utf8") as f:
    TimelineGranularityTemplate_QWEN = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryDocCorTemplate.txt"), "r", encoding="utf8") as f:
    QueryDocCorTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "UsefulReference.txt"), "r", encoding="utf8") as f:
    UsefulReferenceTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "GeneralQueryAnswer.txt"), "r", encoding="utf8") as f:
    GeneralQueryAnswerTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "QueryRetrievalRangeNew.txt"), "r", encoding="utf8") as f:
    QueryRetrievalRangeNewTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "AddReferenceToAnswer.txt"), "r", encoding="utf8") as f:
    AddReferenceToAnswerTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocTitleCOT.txt"), "r", encoding="utf8") as f:
    DocTitleCOTTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocTitleCOT_OneRush.txt"), "r", encoding="utf8") as f:
    DocTitleCOTOneRushTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocTextCOT_OneRush.txt"), "r", encoding="utf8") as f:
    DocTextCOTOneRushTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocTableFigCOT_OneRush.txt"), "r", encoding="utf8") as f:
    DocTableFigCOTOneRushTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocTextCOT.txt"), "r", encoding="utf8") as f:
    DocTextCOTTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocTableFigCOT.txt"), "r", encoding="utf8") as f:
    DocTableFigCOTTemplate = "".join(f.readlines())
    
with open(os.path.join(cur_dir, "QueryAnswerMultiRound.txt"), "r", encoding="utf8") as f:
    QueryAnswerMultiRoundTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocAnswerMix.txt"), "r", encoding="utf8") as f:
    DocAnswerMixTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocAnswerMix_SubAnswer.txt"), "r", encoding="utf8") as f:
    DocAnswerMix_SubAnswerTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocAnswerMix_FinalAnswer.txt"), "r", encoding="utf8") as f:
    DocAnswerMix_FinalAnswerTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimeRewrite.txt"), "r", encoding="utf8") as f:
    TimeRewriteTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "DocAnswerMixWithExample.txt"), "r", encoding="utf8") as f:
    DocAnswerMixWithExampleTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "TimeInsert.txt"), "r", encoding="utf8") as f:
    TimeInsertTemplate = "".join(f.readlines())

with open(os.path.join(cur_dir, "HotEventRelatedQueryS1.txt"), "r", encoding="utf8") as f:
    HotEventRelatedQueryS1Template = "".join(f.readlines())

with open(os.path.join(cur_dir, "HotEventRelatedQueryS2.txt"), "r", encoding="utf8") as f:
    HotEventRelatedQueryS2Template = "".join(f.readlines())