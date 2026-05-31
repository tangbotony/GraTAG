# coding:utf-8
import copy
import random
import re
import time
import json
import tqdm
from collections import Counter

import numpy as np

from include.config import RagQAConfig, PromptConfig, DocQAConfig
from include.logger import log
from include.utils import llm_call
from include.utils.similarity_utils import get_similarity

from include.utils.text_utils import generate_random_string, get_md5, convert_text_to_number


def double_check_for_post_mount_with_number(sentence, reference_text):
    # 对包含数字的挂载进行Double check，要求出现在回答句子当中的所有数字都必须出现在引证句子中
    # 但不能简单地使用字符串操作，否则就会出现回答中出现“1%”，而印证中原文是“1.0%”这种情况未能正确挂载
    # 需要先将字符串转变为数字，比较大小，大小相等视为校验通过
    sentence_number_text = extract_numbers(sentence)
    reference_number_text = extract_numbers(reference_text)
    sentence_number, reference_number = [], []
    for each in sentence_number_text:
        if convert_text_to_number(each):
            sentence_number.append(convert_text_to_number(each))
    for each in reference_number_text:
        if convert_text_to_number(each):
            reference_number.append(convert_text_to_number(each))
    for each_sentence_number in sentence_number:
        if not any([each_reference_number == each_sentence_number for each_reference_number in reference_number]):
            return False
    return True


def is_need_extra_ref(sentence: str):
    """
    判断句子是否需要引证，满足下面所有条件时返回True，即需要引证：
    1. 句子内部没有已引证的内容（即没有形如[ABCD1234]类型的标识）
    2. 句子内部没有井号“#”（md语言中，有井号的一般是标题行无需引证）
    3. 句子没有整个被粗体标识符“**”包住（同样视为标题行）
    4. 句子（有粗体的去除粗体标识符后）不以冒号“：”/“:”结尾
    5. 句子长度不小于10，但当其同时包含粗体标识符“**”和冒号“：”/“:”时，对长度要求提高至20，为了防止形如下面的句子形式挂载无关引证：
    - **时间**：2024年7月
    - **地点**：中国上海
    """
    # 去掉句子最前面的"1.""2."等编号
    prefix = re.match("[0-9]\.", sentence)
    if prefix:
        sentence = sentence.replace(prefix.group(), "")
    sentence = sentence.strip()
    if "**" in sentence and (":" in sentence or "：" in sentence):
        min_length = 20
    else:
        min_length = 10
    if (
            not re.search(r'\[\w+]', sentence)
            and ("#" not in sentence)
            and not (sentence.startswith("**") and sentence.endswith("**"))
            and not any([sentence.strip().strip("*").strip().endswith(char) for char in ":："])
            and len(sentence) >= min_length
    ):
        return True
    return False


def doc_split(doc_content: str):
    doc_content = doc_content.strip()
    sentences_new = re.split(r'([。!！？?\n])', doc_content)
    index = 0
    while index < len(sentences_new):
        if sentences_new[index] == "":
            del sentences_new[index]
            continue
        if index > 0 and re.match(r'\[\w+]', sentences_new[index]):
            ref_pattern = re.compile(r'\[\w+]')
            ref_matches = ref_pattern.finditer(sentences_new[index])
            # ref_matches = list(ref_matches)
            append_left = False
            append_right = 0
            for idx, match1 in enumerate(ref_matches):
                if idx == 0 and match1.start() == 0:
                    append_left = True
                    append_right = match1.end()
                    continue
                if append_right == match1.start() + 1:
                    append_right = match1.end()
            if append_left:
                sentences_new[index - 1] = sentences_new[index - 1] + sentences_new[index][:append_right]
                sentences_new[index] = sentences_new[index][append_right:]
            continue

        if sentences_new[index][0] in ['”', '’'] and index - 1 >= 0:
            sentences_new[index - 1] = sentences_new[index - 1] + sentences_new[index]
            del sentences_new[index]
            continue

        if sentences_new[index] in ['。', '！', '!', '？', '?', '\n']:
            if index - 1 >= 0:
                sentences_new[index - 1] = sentences_new[index - 1] + sentences_new[index]
                del sentences_new[index]
        else:
            index = index + 1
    return sentences_new


def is_number_in_reference(sentence_numbers: list, ref: str):
    for num in sentence_numbers:
        if num in ref:
            return True
    return False


def extract_numbers(sentence):
    # 在最终回答中逐句判断走哪一条后挂载渠道
    # 若句中包含关键数字，则使用llm进行后挂载；
    # 若句中不包含关键数字（如“2024年8月30日”类型的日期，用于表示有序列表的序号“1.”“2.”均视为非关键数字）则使用相似度模型进行挂载
    sentence = sentence.strip()
    numbers = re.findall(r'[\d.%０１２３４５６７８９．％]+', sentence)
    crucial_numbers = []
    origin_sentence = copy.deepcopy(sentence)
    try:
        for each_number in numbers:
            sentence = sentence.partition(each_number)[-1]
            if len(sentence) > 0 and sentence[0] in ["年", "月", "日"]:
                # 排除年份、月份和日期类型的数字
                continue
            if each_number in [".", "．"]:
                continue
            if origin_sentence.startswith(each_number) and each_number.endswith("."):
                # 排除表示有序列表的序号的数字
                continue
            crucial_numbers.append(each_number)
    except:
        return crucial_numbers
    return crucial_numbers


def get_most_similar_sentence(
        sentence: str, reference_lib: dict, sim_threshold_low: float = 0.53, sim_threshold_high: float = 0.6,
        max_ref_per_sentence: int = 1):
    # sentence_numbers = extract_numbers(sentence)  # 使用正则表达式检查句子中是否有数字
    sentence = re.sub(r'\[\w+]', '', sentence)  # 确保输入没有[XXX]
    reference_list = [item["description"] for item in reference_lib.values()]
    reference_id = [item for item in reference_lib.keys()]
    sim_matrix = get_similarity([sentence], reference_list)[0]
    top_n_ref_id = np.argsort(sim_matrix)[::-1]  # 对所有的引证进行倒排

    chosen_ref_ids = []
    for ref_index in top_n_ref_id:
        reference_index = reference_id[ref_index]
        similarity_index = sim_matrix[ref_index]
        # reference_sentence_index = reference_list[ref_index]
        if similarity_index > sim_threshold_high and len(chosen_ref_ids) < max_ref_per_sentence:
            chosen_ref_ids.append(reference_index)
    insert_index = len(sentence) - 1
    while sentence[insert_index] in ['。', '！', '!', '？', '?', '\n']:
        insert_index -= 1
    new_sentence_with_ref = sentence[:insert_index + 1] + "".join(chosen_ref_ids) + sentence[insert_index + 1:]
    used_reference_lib_a = {k: v for k, v in reference_lib.items() if k in chosen_ref_ids}
    return new_sentence_with_ref, used_reference_lib_a


def get_most_similar_sentence_from_llm(sentence: str, reference_lib: dict, QAConfig, parallel_cnt: int = 1,
                                       session_id: str = ''):
    sentence = re.sub(r'\[\w+]', '', sentence)

    reference_list = [item["description"] for item in reference_lib.values()]
    all_lists = []
    prompt_list = []
    chosen_ref_ids = []
    for _ in range(parallel_cnt):
        random.shuffle(reference_list)
        all_lists.append(copy.deepcopy(reference_list))
        references_in_prompt = "\n".join(
            ["[{}]: {}".format(index + 1, each) for index, each in enumerate(reference_list)])
        task_template = PromptConfig["add_reference_to_answer"]["instruction"]
        prompt_list.append(task_template.format(sentence, references_in_prompt))
    start_time = time.time()
    if parallel_cnt > 1:
        result = llm_call(query=prompt_list, model_name=QAConfig["TASK_MODEL_CONFIG"]["add_reference_to_answer"],
                          is_parallel=True, parallel_cnt=parallel_cnt, temperature=0, session_id=session_id, timeout=5)
    else:
        result = [llm_call(query=prompt_list, model_name=QAConfig["TASK_MODEL_CONFIG"]["add_reference_to_answer"],
                           is_parallel=False, temperature=0, session_id=session_id, timeout=5)]
    log.info("post_mount llm prompt: \n{}".format(prompt_list[0]))
    log.info("post_mount llm result: {}".format(result))
    final_reference = []
    for index, each in enumerate(result):
        try:
            if eval(each) < 0:
                final_reference.append("无")
                continue
            final_reference.append(all_lists[index][eval(each) - 1])
        except Exception:
            final_reference.append("无")
    count_final = Counter(final_reference)
    final_reference.sort(key=lambda x: count_final[x], reverse=True)
    right_reference_text = final_reference[0]
    if not double_check_for_post_mount_with_number(sentence, right_reference_text):
        log.info("待挂载引证的句子是：{}！！！！！！！！"
                 "挂载的引证内容是：{}！！！！！！！！！"
                 "Double check未通过...".format(sentence, right_reference_text))
        # double check: 如果句子中的关键数字未能在引证的材料当中找到则不挂载
        return sentence, {}
    log.info("待挂载引证的句子是：{}！！！！！！！！"
             "挂载的引证内容是：{}！！！！！！！！！"
             "用时：{}s".format(sentence, right_reference_text, time.time() - start_time))
    for key, value in reference_lib.items():
        if value["description"] == right_reference_text:
            chosen_ref_ids.append(key)
    insert_index = len(sentence) - 1
    while sentence[insert_index] in ['。', '！', '!', '？', '?', '\n']:
        insert_index -= 1
    new_sentence_with_ref = sentence[:insert_index + 1] + "".join(chosen_ref_ids) + sentence[insert_index + 1:]
    used_reference_lib_a = {k: v for k, v in reference_lib.items() if k in chosen_ref_ids}

    return new_sentence_with_ref, used_reference_lib_a


def add_references_to_doc(
        reference_lib,  # 可以使用的引用来源
        doc,  # 已生成的全文
        QAConfig,
        is_continue_ref=True,
        session_id=''
):
    """
    reference_lib = {
        "[nJsXNa6u]": {
            "id": " ",
            "description": "..."
        },
        "[aZfNApNj]": {
            "id": " ",
            "description": "..."
        }
    }
    """
    if not is_continue_ref:
        doc = re.sub(r'\[\w+]', '', doc)
    if len(doc) < 10:
        return dict(), doc

    # 输入的文本片段的拆分
    sentences = doc_split(doc)

    # def helper(sentence):
    #     user_reference_lib = dict()
    #     if is_need_extra_ref(sentence):
    #         res, user_reference_lib = get_most_similar_sentence(sentence, reference_lib)
    #     else:
    #         res = sentence
    #     return res, user_reference_lib
    #
    # pool = ThreadPool(processes=3)
    # explanation_results = pool.map(helper, sentences)
    # pool.close()
    # pool.join()

    all_res = []
    res_reference_lib = dict()
    # for res_i, lib_i in explanation_results:
    #     all_res.append(res_i)
    #     res_reference_lib.update(lib_i)
    for each in sentences:
        if is_need_extra_ref(each):
            crucial_numbers = extract_numbers(each)
            if len(crucial_numbers) > 0:
                log.info("句子：\n{}\n中包含关键数字：{}".format(each, crucial_numbers))
                res, ref_lib = get_most_similar_sentence_from_llm(each, reference_lib, QAConfig, session_id=session_id)
            else:
                res, ref_lib = get_most_similar_sentence(each, reference_lib)
        else:
            res, ref_lib = each, {}
        all_res.append(res)
        res_reference_lib.update(ref_lib)

    final_doc = "".join(all_res)
    final_doc = re.sub("\\[资料[0-9a-zA-Z,，\\s]+]", "", final_doc)
    return res_reference_lib, final_doc


def main_1():
    start_time = time.time()
    answer = """#### 市场表现
        在2024年09月09日，A股市场经历了一次显著的下跌，具体表现如下：
        - **上证指数**下跌0.92%。
        - **深证成指**下跌0.74%。
        - **创业板指**下跌0.23%。

        #### 影响因素
        此次大跌的主要原因可以从以下几个方面进行分析：

        1. **全球金融市场波动**：
        - **欧美股市大跌**：上周五欧美股市大跌，特别是科技股的抛售潮，对A股市场产生了负面影响。
        - **亚太股市普跌**：亚太股市的普跌进一步加剧了市场的不稳定情绪。

        2. **美联储降息预期**：
        - **降息幅度**：虽然9月美联储降息几乎已是板上钉钉，但市场对降息幅度的预期存在分歧，部分市场参与者预计降息幅度可能超过预期，这导致了市场的普遍下跌。
        - **经济衰退担忧**：美国经济数据不佳，特别是就业数据的不理想，加剧了市场对经济衰退的担忧，进一步推动了降息预期。

        3. **地缘政治因素**：
        - **中东局势**：虽然地缘政治的影响偏中性，但巴以双方在关键问题上的分歧和态度强硬，对中东局势的恢复不利，增加了市场的不确定性。

        4. **国内因素**：
        - **权重股调整**：银行、白酒、煤炭、有色金属等板块的权重股跌幅明显，对市场整体表现产生了重要影响。
        - **资金面紧张**：市场资金面紧张，交投低迷，两市成交额回升幅度有限，进一步加剧了市场的震荡。

        #### 对投资者的影响
        此次大跌对投资者的影响主要体现在以下几个方面：

        1. **市场信心受挫**：大跌导致市场信心减弱，投资者对市场的短期前景持谨慎态度。
        2. **投资策略调整**：投资者可能需要调整投资策略，更加注重风险管理和资产配置的平衡。
        3. **资金流动变化**：市场波动可能导致资金流向变化，投资者可能选择将资金从风险较高的资产类别中撤出，转而投向避险资产。

        #### 对全球经济的潜在影响
        此次大跌不仅对国内市场产生了直接影响，还可能对全球经济产生一定的潜在影响：

        1. **全球金融市场联动**：由于全球金融市场的高度联动性，A股市场的大幅下跌可能引发全球金融市场的波动。
        2. **国际贸易影响**：地缘政治的不确定性可能影响国际贸易，特别是中东地区的局势变化可能对全球能源市场产生影响。
        3. **全球资本流动**：市场的不稳定可能促使资本在全球范围内重新配置，寻求更稳定的投资环境。

        #### 政府或监管机构的应对措施
        面对市场的大幅下跌，政府和监管机构可能会采取以下措施：

        1. **政策支持**：政府可能会出台一系列政策措施来稳定市场预期，提振投资者信心。例如，证监会可能会推出一揽子政策措施来活跃资本市场。
        2. **市场监管**：监管机构可能会加强市场监管，确保市场秩序的稳定和投资者权益的保护。
        3. **流动性支持**：央行可能会通过多种手段提供流动性支持，确保市场资金面的稳定。

        #### 市场恢复情况
        对于市场的恢复情况，需要密切关注以下几个方面的变化：

        1. **政策效应**：政府和监管机构的政策措施对市场恢复的影响。
        2. **资金面变化**：市场资金面的变化对市场恢复的重要性。
        3. **国际形势**：国际经济形势的变化对A股市场的影响。

        综上所述，A股市场在2024年09月09日的大跌是多种因素共同作用的结果，包括全球金融市场波动、美联储降息预期、地缘政治因素以及国内资金面紧张等。这些因素的综合作用导致了市场的不稳定性。未来市场的恢复将取决于政策效应的发挥、资金面的变化以及国际形势的发展。"""

    reference_text = """
    期市早餐2024.09.09：两个月合计下修了8.6万新增就业人口。失业率降至4.2%，符合预期，为连续四个月上升以来首次下降，前值为4.3%。【核心逻辑】整体来看，美国8月就业数据环比有所改善，失业率小幅回落，但“萨姆规则”的衰退预警依旧被触发，因此该数据并未强劲到大幅改善当前市场对美国经济衰退的担忧。正如我们在《当前博弈点与交易主线下的人民币汇率演绎展望》一文中所述，当前市场对美联储的降息预期以及对美国经济的衰退预期或过于激进和悲观，若想上述市场预期得到一定程度的修正，需看到更多强劲的美国经济数据来证伪。因此，短期内市场风险偏好大概率仍呈现承压状态，“衰退交易”大概率仍将与“降息交易”穿插进行。
    期市早餐2024.09.09：但经济衰退担忧以及周五美联储官员讲话仍预示美联储9月可能降息25BP，引发金融资产普跌现象，VIX指数上升，贵金属市场亦不能幸免，但年内降息次数预期明显上升，这预示11月及12月降息50BP概率上升。我们认为，美联储9月降息25BP或是大概率事件，然9月降息幅度低于预期下贵金属价格仍有调整力，但金融资产的下跌以及对经济衰退担忧，将助推美联储后续降息50BP可能性大幅上升。
    期市早餐2024.09.09：因此，在极端情况未发生前，短期内美元兑人民币即期汇率大概率将稳定在当前水平。【风险提示】中国经济表现超预期、海外经济体表现超预期股指：交投低迷，延续震荡上周五股指集体收跌，大盘股指相对抗跌，以沪深300指数为例，收盘下跌0.81%。从资金面来看，两市成交额回升77.94亿元。期指方面，IF、IC放量下跌，IH、IM缩量下跌。1、美国8月非农新增就业14.2万人不及预期，前值大幅下修，失业率降至4.2%，薪资增幅高于预期。中国8月CPI、PPI。中国社会融资规模、新增人民币贷款、M0、M1、M2。美国8月非农报告喜忧参半，美联储理事沃勒鸽派发声，不排除未来数据恶化后更大幅度降息。
    期市早餐2024.09.09：而资金面则放大了这一影响。除此之外，近期地缘政治的影响偏中性，一方面巴以新一轮的停火谈判即将重启，白宫甚至宣称加沙停火协议90%部分已达成一致；另一方面，巴以双方在一些关键问题存在分歧，且态度较为强硬，不是特别利好于中东局势的恢复。后续还需关注中东局势的走向。【南华观点】后续预计期价大体趋势偏震荡下行的概率仍然较大，但在船公司动作和地缘政治的影响下，可能出现短期反弹。
    期市早餐2024.09.09：进口利润：目前沪铝现货即时进口盈利-828元/吨，沪铝3个月期货进口盈利-849元/吨。成本：氧化铝边际成本3302元/吨，电解铝加权完全成本17781元/吨。【核心逻辑】铝：展望后市，短期宏观情绪主导下或有超跌可能，待情绪释放旺季背景下仍有温和反弹机会。美国经济数据以及降息25BP概率的走强，为上周引发铝价下跌大的主要因素。随着铝价回落，国内北方基差走强愈发显著，社库去化亦有好转，国内出货情况整体受到价格回落提振，叠加下游加工端开工率持续走强，表明旺季备库阶段基本面仍有一定支撑。此外，海外库存持续回落，伦铝基差再度走高。氧化铝：强现实弱预期格局维持，近月合约下方支撑仍强。
    期市早餐2024.09.09：氧化铝受宏观情绪拖累，截至周五收盘主力收于3992元/吨，周环比+1.66%。【宏观环境】上周公布的美国制造业PMI继续萎缩且低于预期，周内公布的美职位空缺数低于预期、ADP就业不及预期、挑战者裁员大超预期、以及非农就业新增不及预期且前值下修，进一步凸显美就业市场降温。经济衰退担忧以及周五美联储官员讲话仍预示美联储9月可能降息25BP，造成有色金属普跌。【产业表现】供给及成本：供应端，上周电解铝产量83.04万吨，环比+0.24万吨，氧化铝产量163.1万吨，环比-3.2万吨，氧化铝与电解铝周度产量比值1.96，环比-0.04。
    A股突发！1分钟巨震：全球资本市场再度陷入震荡，上周五欧美股市大跌，今天上午，亚太股市普跌，日经225指数、韩国综合指数跌幅较大。A股多只人气股巨震。上午一开盘，深圳华强、大众交通（600611）、科森科技（603626）、锦江在线（600650）、大众公用（600635）、金龙汽车（600686）、创识科技（300941）等个股在1分钟左右的时间里直线跳水，其中，大众交通、科森科技均迎来“天地板”。截至上午收盘，上证指数下跌0.92%，深证成指下跌0.74%，创业板指下跌0.23%。医药股走强今天上午，医药股表现活跃，细胞免疫治疗、医疗服务、民营医院、医疗器械等板块大涨。其中，细胞免疫治疗板块大爆发，冠昊生物（300238）、阳普医疗（300030）等个股迎来20%涨停。商务部网站9月8日消息，近日，商务部、国家卫生健康委、国家药监局联合印发关于在医疗领域开展扩大开放试点工作的通知。通知提出，为引进外资促进我国医疗相关领域高质量发展，更好满足人民群众医疗健康需求，拟在医疗领域开展扩大开放试点工作。通知明确，在生物技术领域，自通知印发之日起，在中国（北京）自由贸易试验区、中国（上海）自由贸易试验区、中国（广东）自由贸易试验区和海南自由贸易港允许外商投资企业从事人体干细胞、基因诊断与治疗技术开发和技术应用，以用于产品注册上市和生产。所有经过注册上市和批准生产的产品，可在全国范围使用。拟进行试点的外商投资企业应遵守我国相关法律、行政法规等规定，符合人类遗传资源管理、药品临床试验（含国际多中心临床试验）、药品注册上市、药品生产、伦理审查等规定要求，并履行相关管理程序。通知明确，拟允许在北京、天津、上海、南京、苏州、福州、广州、深圳和海南全岛设立外商独资医院（中医类除外，不含并购公立医院）。设立外商独资医院的具体条件、要求和程序等将另行通知。另外，国家发展改革委网站9月8日发布《外商投资准入特别管理措施（负面清单）（2024年版）》。负面清单限制措施由31条减至29条，删除了“出版物印刷须由中方控股”，以及“禁止投资中药饮片的蒸、炒、炙、煅等炮制技术的应用及中成药保密处方产品的生产”2个条目，制造业领域外资准入限制措施实现“清零”。对于医药板块，目前机构普遍持乐观态度，认为在行业基本面迎来向上拐点、创新催化不断、政策持续鼓励支持等因素下，板块有望迎来修复行情。国金证券看好四主线：第一，创新药，建议关注国内创新药各细分赛道龙头的数据披露；第二，医疗器械，看好国内细分领域国产医疗器械龙头公司的成长性，以及下半年院内需求复苏带来的业绩弹性；第三，中药，在卫生总费用支出增加、国家对银发经济重视等大背景下，中药领域提供老龄化、慢性病相关用药的公司值得关注；第四， CXO及医药上游，企业持续推进产品创新，蓄力发展。权重股调整今天上午，银行、白酒、煤炭、有色金属等板块集体调整，其中，中国石油、中国石化、招商银行、中国神华（601088）、海尔智家（600690）、紫金矿业（601899）、洛阳钼业（603993）、泸州老窖（000568）等权重股跌幅明显。上述个股中，大多数都具有高股息特征。最近，高股息资产持续调整，后市该如何看待？有市场人士认为，在以下三方面因素作用下，业绩波动较低且高分红的方向依然会是资金配置的重要方向。首先，低利率环境下的配置优势。在低利率甚至负利率成为常态的全球经济背景下，高股息率的红利资产为投资者提供了相对较高的无风险或低风险收益率。其次，历史数据与趋势分析。从历史数据看，中国10年期国债收益率与中证红利指数之间的负相关关系表明，在国债收益率处于低位时，红利资产往往具有较好的市场表现。当前，我国10年期国债收益率维持在低位水平，为高股息资产的运行提供了良好的市场环境。最后，政策支持。新“国九条”进一步强调了长期价值投资的重要性，高股息及稳健分红板块作为符合这一投资理念的重要方向，有望在未来获得更多政策支持和市场关注。关注同花顺财经（ths518），获取更多机会
    期市早餐2024.09.09：3、加工环节的产量在上周均表现出回暖，进入季节性旺季，环比有所改善，但同比表现或存疑。【核心观点】供给侧风险在OZ投产的消息之下有所降温，虽然OZ在2024年的产量并不改变今年矿紧张的局面，在前期高点已经对矿项目投产的不确定性计价，叠加消费在高价状态下难以维持，盘面面临较大回调压力。在价格大幅回落之后，冶炼成本和消费或能提供一定支撑，关注22500支撑。锡：宏观主导短期走势【盘面回顾】沪锡主力期货合约在周中回落3.91%至25.3万元每吨；上期所库存回落上千吨至9794吨，LME库存稳定在4600吨附近。
    期市早餐2024.09.09：虽然9月美联储降息几乎已是板上钉钉，但是经济数据不佳使得投资者加码第四季度降息幅度。展望未来一周，宏观数据带来的影响或需要1-2个交易日发酵，因此铜价短期仍有下降可能性，降幅有限。基本面并无太大变化，供给端没有放量的迹象，需求方面部分板块存在两点，但是没有明显的增长点。【南华观点】震荡偏弱，周运行区间7.08万-7.29万元每吨。铝产业链：宏观压力较大，短期存在超跌可能【盘面回顾】上周铝价流畅下跌，截至周五沪铝主力收于19310元
    期市早餐2024.09.09：价格大幅下跌之下，下游补库驱动较好，且临近交割，预计现货流动环比收紧，升水预计继续保持坚挺；月差有支撑。【宏观环境】周内公布的美国制造业PMI继续萎缩且低于预期令有色板块普跌，叠加周内公布的美职位空缺数低于预期、ADP就业不及预期、挑战者裁员大超预期、以及非农就业新增不及预期且前值下修，进一步凸显美就业市场降温显示，并助推周内美联储降息50BP预期升温下美指与美债收益率双双回落。但经济衰退担忧以及周五美联储官员讲话仍预示美联储9月可能降息25BP，引发金融资产普跌现象，VIX指数上升。金融资产的下跌以及对经济衰退担忧，将助推美联储后续降息50BP可能性大幅上升。
    期市早餐2024.09.09：。【核心观点】总体过剩格局依然给盘面世家压力，短期价格反弹后基于锂盐厂存在套保机会，价格下跌后得加旺季临近，下游有一定补库动作，贸易商也有所采买，但是依然无法使盘面有较好的反弹持续性。9月电池排产环增尚可，关注潜在补库支撑力度，总体上建议依然偏空对待，
    期市早餐2024.09.09：美国8月非农报告喜忧参半，美联储理事沃勒鸽派发声，不排除未来数据恶化后更大幅度降息。此消息本该利好A股，但就业数据中的不佳部分主导市场情绪，上周五美股大跌，且根据前期行情，当前降息预期变化对A股影响较小，因此具体影响有待观察。近期各股指震荡整理，沪深两市成交金额不足6000亿元，指数压力仍然偏大。当前宏观环境与市场状态下，市场信心偏弱，增量资金不足，难以形成趋势性行情。后续股指想形成趋势性的上行，需要看到内需复苏或资金流入等明确的信号，短期内这些方面的信号仍不明确，需要等待政策生效和时间修复。国债：多头继续持有【行情回顾】：期债早盘低开后震荡上行，午后随着A股跌幅扩大进一步走高收涨。
    活跃资本市场一揽子措施出台  A股或成全球资产配置的“核心战场”：“上市公司质量的提升，最终要体现在它的价值创造能力。建议继续抓好新一轮提高上市公司质量三年行动方案的实施，推动上市公司提升治理能力、竞争能力、创新能力、抗风险能力。”刘健认为，应进一步引导上市公司通过现金分红、股份回购等方式增强对股东的回报，夯实中国特色估值体系的内在基础，切实提升投资者的获得感和对资本市场的信心。从融资端来看，一揽子举措除提到建立完善突破关键核心技术的科技型企业上市融资、债券发行、并购重组“绿色通道”外，还提到了“积极研究更多满足科技型企业需求的融资品种和方式，研究建立科创板、创业板储架发行制度。
    活跃资本市场一揽子措施出台  A股或成全球资产配置的“核心战场”：”富国基金总经理陈戈如是点评。陈戈指出，从政策定位上看，一揽子举措既立足当下，从投资端、融资端、交易端等方面全面入手，稳定预期、提振信心；又着眼长远，坚持改革开路，统筹发展股票、债券、期货市场，完善资本市场基础制度，为积极构建高效、活跃的多层次资本市场保驾护航；既着眼于持续优化资本市场长期发展生态；又积极谋求实现资本市场与实体经济的良性互动。关于这些举措可能会在哪些方面更快产生实效，陈戈认为，降低交易环节费用的相关措施，将立竿见影地减轻交易环节的摩擦成本，对于个人投资者及机构投资者均是利好。
    活跃资本市场一揽子措施出台  A股或成全球资产配置的“核心战场”：申万宏源证券董事长刘健同样表示，资本市场活跃度与交易产品、交易机制、交易便利性密不可分，提高交易产品多样性和交易机制灵活性，能更加满足投资者的各类投资需求。对于下一步的建议，刘健表示，一是推进权益类、债券类、商品类及其他金融衍生品实行注册发行，加快完善市场基础工具体系，在推出中证1000股指期货期权的基础上，推出深成指100、科创50等股指期货及30年国债期货等长期限产品。二是发挥衍生品市场的定价和预期引导功能，为投资者提供更多的风险对冲工具。三是在交易方式上，除传统代理交易外，鼓励投资者及市场交易商积极探索量化交易、衍生品交易和跨境交易等新形式，在更好满足投资者差异化投资配置需求。
    深市上市公司公告（9月9日）：诺德股份自查显示，今年4月10日公司披露了《诺德新材料股份有限公司关于拟收购云财富期货有限公司90.2%股权的公告》，但20天后的4月30日，公司就收到了吉林证监局出具的《关于对诺德新材料股份有限公司及相关责任人采取出具警示函措施的决定》，一个月后的5月31日，公司又收到上交所出具的《关于对诺德新材料股份有限公司及相关责任人予以监管警示的决定》，认定公司在收购云财富期货有限公司90.2%股权交易时，未及时披露签署上述框架协议相关事项。当晚，东旭集团两家上市公司——ST旭蓝、ST旭电，均被立案调查。ST旭蓝发布公告称，因涉嫌信息披露违法违规，证监会决定对公司及公司控股股东东旭集团立案。
    M3DAO资讯频道：2）本轮美联储降息的可能影响美联储的降息预期已经开始对全球金融市场和资本流动产生影响，为了应对经济下行压力，英国、欧央行的降息押注也在升温。此前有投资者认为，现在英国央行9月份降息的可能性超过50%。对于欧洲央行而言，交易员预计到10月份将降息两次，并且距离9月份大幅降息的预期并不远。   接下来，我们来看看本轮降息可能会带来的一些影响：A、对全球市场的影响本次美联储降息预计将对全球金融市场产生显著影响。首先，美元利率的降低可能促使资金流向收益率更高的市场和资产，导致全球资金流动增加。降息还可能使得美元贬值，可能引发汇率波动，并推动以美元计价的商品价格上涨，如原油和黄金。
    活跃资本市场一揽子措施出台  A股或成全球资产配置的“核心战场”：海外经济方面，通胀回落至疫情前水平尚需时日，全球金融稳定风险上升，经济前景和货币政策不确定性上升。结合地产、城投等领域的风险扰动，外汇市场的波动等，回应投资者关切、提振投资者信心在当下显得非常及时必要。“今年是党的二十大开局之年，亦是三年疫情全面结束的修复之年，经济企稳复苏是发展主线，但高质量发展的路线坚定不移，推动现代产业体系建设、壮大战略新兴产业、打造更多支柱产业纲举目张。而经济的高质量发展和产业转型升级，需要资本市场与实体经济的良性互动。”陈戈表示。陈戈指出，一方面，要让金融市场更好地服务赋能实体经济转型；另一方面，也要让金融市场充分分享实体经济高质量发展的红利。
    活跃资本市场一揽子措施出台  A股或成全球资产配置的“核心战场”：“我们观察解读经济形势，既要看清短期的、阶段性的‘形’,更要读懂长期的、根本性的‘势’；在看到短期困难挑战和阶段性压力的同时，更要增强长期发展的信心和耐心。”该专家认为，应做到客观看待当前经济发展的速度、准确把握经济运行中的亮点、坚定对重点领域风险化解的信心。新一轮回报周期到来，A股或成全球资产配置核心战场“经历政策底、经济底、情绪底的震荡夯实以后，A股市场有望迎来新一轮回报周期。”陈戈如是认为。首先，“7.24政治局会议”不仅表明A股市场“政策底”的出现，证监会日前一揽子措施的出台，将进一步为活跃资本市场的政策支持。
    M3DAO资讯频道：全球经济联动：由于全球经济高度相互关联，美国作为全球最大经济体，其经济状况对其他国家经济也具有重要影响。美联储通过货币政策调控美国经济，也会影响全球经济的走势。风险资产价格波动：美联储的政策举措对风险资产（如股票、债券、大宗商品）价格产生重要影响。市场对美联储政策的解读和预期会直接影响全球风险资产市场的波动。总体来说，由于美国经济的重要性和美元的全球地位，美联储的政策举措对全球金融市场产生深远和直接的影响，因此其决策备受全球市场关注。
    银河证券：2024年A股市场将呈现震荡上行格局：其次是扩大内需方面。相较于2021年和2022年，本次会议对于扩大内需有更加全面细致的阐述。2024年扩大内需要更加重视消费与投资的相互影响效应，鼓励未来相关方向的投资。此外，要发挥政府在投资方面的带动放大效应，主要涉及“关键核心技术攻关、新型基础设施、节能减排降碳”等领域的投资。再次是改革开放方面。2024年要深化重点领域的改革，其中“财税体制改革”和“金融体制改革”是前两年的中央经济工作会议中未提及的，表明明年相关改革措施会相应增多，继续关注后续政策。对外开放方面，会议特别提出放宽“电信、医疗”等服务业市场准入，打造“投资中国”品牌。
    活跃资本市场一揽子措施出台  A股或成全球资产配置的“核心战场”：“申万宏源将进一步树牢为人民服务、为客户服务的理念，创设满足不同类型客户风险和收益偏好的交易产品，更好满足资产市场投资需要。”刘健表示。“对于富国基金而言，未来将不断落实好一揽子政策措施，积极发挥机构投资者的优势，不断提升专业能力，深入研究，勇于创新，积极为资本市场高质量发展贡献力量。”陈戈表示。三端综合施策，股份回购、储架发行制度是“利器”此次证监会确定了从投资端、融资端、交易端一揽子协同发力的政策措施。陈戈认为，这些措施剑指资本市场高质量发展，投资端，上市公司股份回购制度的进一步优化值得期待；融资端，科创板、创业板储架发行制度值得进一步关注。
        """

    reference_list = reference_text.strip().split("\n")
    reference_dict = {}
    for each_ref in reference_list:
        reference_dict[generate_random_string(each_ref, 8)] = {
            "id": get_md5(each_ref),
            "description": each_ref,
            "title": "",
            "url": "",
            "source": "2",
            "source_id": "2024-2-20-2",
            "source_name": "用户上传数据库"
        }
    res_1 = add_references_to_doc(reference_dict, answer, RagQAConfig)
    end_time = time.time()
    print("总用时：{}".format(end_time - start_time))
    print(res_1)


def main_2():
    pdf_id_map_file_path = '../../pipeline_doc/data/pdf_name_id_map.json'
    with open(pdf_id_map_file_path, 'r', encoding='utf-8') as pdf_id_map_file:
        pdf_id_map = json.load(pdf_id_map_file)
    process_file_path = "../../pipeline_doc/data/use_data_v2.json"
    with open(process_file_path, 'r', encoding='utf-8') as process_file:
        process_content = json.load(process_file)
    save_list = []
    for item in tqdm.tqdm(process_content):
        tmp_answer = item["answer"]
        tmp_ref = item["ref"]
        ref_answer = []
        pdf_content = ""
        # ref_answer
        for ref_key, ref_val in tmp_ref.items():
            _id = ref_val["id"]
            news_id = pdf_id_map[ref_val["source_id"]]
            content = ref_val["description"]
            origin_content = ref_val["description"]
            poly = eval(ref_val["other_info"].get("chunk_poly", ""))
            poly = list(map(str, poly))
            page_num = ref_val["other_info"].get("page_num", 0)
            # try:
            poly_save = str(page_num) + "," + ','.join(poly)
            # except:
            #     print(1)

            tmp_ref_answer = {
                "_id": _id,
                "news_id": news_id,
                "content": content,
                "origin_content": origin_content,
                "poly": [poly_save]
            }
            ref_answer.append(tmp_ref_answer)
            pdf_content += content

        # ref_page
        pdf_name = ref_val["source_id"]
        pdf_id = pdf_id_map[ref_val["source_id"]]
        tmp_ref_page = {"_id": pdf_id, "url": "", "site": "", "title": "", "summary": "", "content": pdf_content,
                        "icon": "", "all_info": ref_val["other_info"]}
        ref_page = {pdf_id: tmp_ref_page}
        # input
        question = ref_val["raw_input"]
        query = question + str([pdf_name])
        # stream_info
        _, tmp_final_answer = add_references_to_doc(tmp_ref, tmp_answer, DocQAConfig)
        tmp_final_answer_split = doc_split(tmp_final_answer)
        stream_info = []
        for answer_item in tmp_final_answer_split:
            tmp_char_item = {"text": answer_item}
            stream_info.append(tmp_char_item)
        tmp_save_content = {"query": query, "ref_answer": ref_answer, "ref_page": ref_page, "stream_info": stream_info}

        save_list.append(tmp_save_content)
    save_path = "../../pipeline_doc/data/tmp_test_v6.json"
    with open(save_path, 'w', encoding="utf-8") as save_file:
        json.dump(save_list, save_file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main_1()
