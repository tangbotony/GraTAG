# coding:utf-8
import time
import traceback
import datetime
from multiprocessing.dummy import Pool as ThreadPool

from include.logger import log
from include.utils.llm_caller_utils import llm_call
from include.utils.similarity_utils import get_similarity
from include.config import PromptConfig, TimeLineConfig
import re
import json
import yaml
from include.utils import clean_json_str, compare_date, dynamic_threshold, text_truncated
import os
from include.utils.Igraph_utils import IGraph, ArcNode
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from include.utils.similarity_utils import find_best_unrelated_subgroup
from include.utils.timeline_utils import get_dag_query_list,complete_sentence

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

def getEventExtractSub(chunkInfoDict, modelName=TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["event_info_extract"], clogger=log,newQuery:str=None, session_id=''):
    """
    对内容进行信息抽取，返回抽取列表
    :return: result:  {"Result": [{"事件发生时间": "2024-05-08 15:59","结束时间": "2024-05-08 15:59","人物": ["习近平","马克龙"],"地点": "法国","事件主体": "中法双方","事件摘要": "中法双方发表关于中东局势、人工智能和全球治理、生物多样性与海洋、农业交流与合作4份联合声明，签署近20项双边合作文件","事件标题": "中法签署20项双边合作文件并发表声明"},{"事件发生时间": "2024-05-08 15:59","结束时间": "2024-05-08 15:59","人物": ["习近平"],"地点": "塞尔维亚","事件主体": "中塞两国","事件摘要": "共同宣布构建新时代中塞命运共同体，塞尔维亚成为第一个和中国共同构建命运共同体的欧洲国家", "事件标题": "中塞共建新时代命运共同体"},{"事件发生时间": "2024-05-08 15:59","结束时间": "2024-05-08 15:59","人物": ["习近平"],"地点": "塞尔维亚","事件主体": "中国","事件摘要": "习主席宣布中方支持新时代中塞命运共同体建设的首期6项务实举措", "事件标题": "习主席支持中塞共建命运共同体"}]}
    """


    jsonTemp = PromptConfig["timeline_event_extract"]["example"]
    ks = ['事件主体', '事件摘要', '事件标题', '事件发生时间', '事件是否是新闻主题的时间线内容']
    ks2Str = str(ks)
    callContent = chunkInfoDict['Chunk']

    publish_time = chunkInfoDict['PublishTime']

    task_prompt_template = PromptConfig["timeline_event_extract"]["GPT_input_item"]
    prompt = task_prompt_template.format(ks2Str=ks2Str, callContent=callContent, query=newQuery, jsonTemp=jsonTemp,publish_time=publish_time)
    jsonData = [{'事件发生时间': 'xxxx-xx-xx xx:xx:xx', '结束时间': 'xxxx-xx-xx xx:xx:xx', '核心人物': [], '地点': [], '事件主体': '', '事件摘要': '', '事件标题': ''}] #兜底返回原始query
    max_try_cnt = TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["max_try_cnt"]
    for retry_cnt in range(max_try_cnt):
        try:
            gpt_res = llm_call(query=prompt, model_name=modelName, clogger=clogger,
                               temperature=TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["temperature"], 
                               top_p=TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["top_p"],
                               session_id=session_id)
            content = clean_json_str(gpt_res)
            jsonData = json.loads(content)
            break
        except:
            clogger.warning("event extract occurs error: {}, will retry, retry cnt:{}/{}.".format(traceback.format_exc(), retry_cnt, max_try_cnt))
            continue

    return jsonData, prompt

def getEventExtract(res:dict=None, chunkInfoDict:dict=None, prompt:str=None):
    """"""
    try:
        if res['Result'].__len__() != 0: #如果gpt4直接返回的不是空列表，或者getEventExtractSub返回的是infoResult
            if isinstance(res['Result'], list): #只处理gpt4直接返回的列表中的结果数据
                for kv in res['Result']:
                    # 标准化时间格式
                    if '事件发生时间' in kv:
                        kv['事件发生时间'] = normalize_datetime(kv['事件发生时间'])
                    if chunkInfoDict['PublishTime']:
                        chunkInfoDict['PublishTime'] =  normalize_datetime(chunkInfoDict['PublishTime'])

    except:
        res={'Result':[]}
    tableDict = {
        'Chunk': chunkInfoDict['Chunk'],
        'Result': res,
        'PublishTime': chunkInfoDict['PublishTime'],
        'Prompt': prompt
    }
    return tableDict

def checkEvents(event_list,url,chunkID, publish_time,doc_id, retrieval_range):
    standard_events = []
    start_time = retrieval_range.get("start_time", "")
    end_time = retrieval_range.get("end_time", "")
    standard_keys = ["事件发生时间", "事件主体", "事件摘要", "事件标题","事件是否是新闻主题的时间线内容"]
    # 只添加包含必要key的事件
    for result in event_list:
        use_flag = 1
        for key_item in standard_keys:
            if key_item not in result:
                use_flag = 0
                break
        if use_flag:
            if "x" in result["事件发生时间"][0:3]:
                use_flag = 0
            ymd=result["事件发生时间"].split(" ")[0]
            if len(ymd) < 10:
                use_flag = 0
        if use_flag and "事件是否是新闻主题的时间线内容" in result:
            if result["事件是否是新闻主题的时间线内容"] != "是":
                use_flag = 0
        if use_flag:
            if not compare_date(result["事件发生时间"], publish_time):
                use_flag = 0
        if use_flag and start_time:
            if not compare_date(result["事件发生时间"], start_time, date_type="start"):
                use_flag = 0
        if use_flag and end_time:
            if not compare_date(result["事件发生时间"], end_time):
                use_flag = 0
        if use_flag:
            now = datetime.datetime.now()
            now_time = now.strftime('%Y-%m-%d %H:%M:%S')
            if not compare_date(result["事件发生时间"], now_time):
                use_flag = 0
        if use_flag:
            if isinstance(result["事件主体"], list):
                result["事件主体"] = " ".join(result["事件主体"][:1]) #只获取一个主体
            elif isinstance(result["事件主体"], str):
                 result["事件主体"] = " ".join([data for data in result["事件主体"].replace("，", ",").split(",") if data.strip()][:1])
            if isinstance(result["事件摘要"], list):
                result["事件摘要"] = ",".join(result["事件摘要"])
            if isinstance(result["事件标题"], list):
                result["事件标题"] = ",".join(result["事件标题"])
            result["事件摘要"] = text_truncated(result["事件摘要"])
            result['url'] = url
            result['chunk_id'] = chunkID
            result["doc_id"] = doc_id
            standard_events.append(result)
    return standard_events


def normalize_datetime(date):
    # 如果只有日期且没有空格，增加空格方便后续日期匹配
    if len(date) == 10:
        date = date+ " "
    add_bc_time=False #是否为公元前
    if date.count("-")==3 and date[0]=="-":
        date=date[1:]
        add_bc_time=True
    elif "公元前" in date:
        add_bc_time=True
    # 提取年份
    year_match = re.search(r'(\d{3,4})', date)
    year = year_match.group(1) if year_match else 'xxxx'
    if len(year) == 3:
        year = "0" + year
    if add_bc_time:
        if (not year) or year == "xxxx":
            year_match = re.search(r'公元前(\d{1,4})年', date)
            year_match_century = re.search(r'公元前(\d{1,2})世纪', date)
            year_match_noyear = re.search(r'公元前(\d{1,4})', date)
            if year_match:
                year = '0'*(4 - len(year_match.group(1))) + year_match.group(1)
            elif year_match_century:
                century = max(int(year_match_century.group(1)) - 1, 1)
                century = str(century)[:2]
                if len(century) == 1:
                    year = "0" + century+ "00"
                else:
                    year = century+ "00"
            elif year_match_noyear:
                year = '0' * (4 - len(year_match_noyear.group(1))) + year_match_noyear.group(1)
            else:
                year = 'xxxx'
        year="-"+year
    

    # 提取月份
    if date.count("-") == 2:
        month_match = re.search(r'-(\d{2})-', date) or re.search(r'-(\d{1})-', date)
        month = month_match.group(1) if month_match else 'xx'
    elif date.count("-") == 1:
        month_match = re.search(r'-(\d{2})', date) or re.search(r'-(\d{1})', date)
        month = month_match.group(1) if month_match else 'xx'
    elif "月"in date:
        month_match = re.search(r'(\d{2})月', date) or re.search(r'-(\d{1})月', date)
        month = month_match.group(1) if month_match else 'xx'      
    else:
        month = 'xx'
    if len(month) == 1:
        month = "0" + month
    if month == "00":
        month = "xx"
    if month != "xx" and int(month) > 12:
        month = "xx"

    # 提取日期
    # 如果没有月份的信息，日期提出来也没有意义。
    if month == "xx":
        day = "xx"
    elif date.count("-") == 2:
        day_match = re.search(r'-(\d{2}) ', date) or re.search(r'-(\d{1}) ', date)
        day = day_match.group(1) if day_match else 'xx'
    elif "日" in date:
        day_match = re.search(r'(\d{2})日', date) or re.search(r'(\d{1})日', date)
        day = day_match.group(1) if day_match else 'xx'
    else:
        day = 'xx'
    if len(day) == 1:
        day = "0" + day
    if day == "00":
        day = "xx"
    if day != "xx" and int(day) > 31:
        day = "xx"

    # 提取小时
    # 没有日期，时间无意义
    if day == "xx":
        hour = "xx"
    else:
        hour_match = re.search(r'(\d{2}):', date) or re.search(r'(\d{1}):', date)
        hour = hour_match.group(1) if hour_match else 'xx'
    if len(hour) == 1:
        hour = "0" + hour
    if hour != "xx" and int(hour) > 24:
        hour = "xx"
    # 提取分钟
    # 如果没有小时的信息，分钟提出来也没有意义。
    if hour=="xx":
        minute = 'xx'
    elif date.count(":") == 2:
        minute_match = re.search(r':(\d{2}):', date) or re.search(r':(\d{1}):', date)
        minute = minute_match.group(1) if minute_match else 'xx'
    elif date.count(":") == 1:
        minute_match = re.search(r':(\d{2})', date) or re.search(r':(\d{1})', date)
        minute = minute_match.group(1) if minute_match else 'xx'
    else:
        minute = 'xx'
    if len(minute) == 1:
        minute = "0" + minute
    if minute != "xx" and int(minute) > 60:
        minute = "xx"

    # 提取秒
    # 如果没有分钟的信息，秒提出来也没有意义
    if minute=="xx":
        second = 'xx'
    elif date.count(":") == 2:
        second_match = re.search(r':(\d{2})$', date) or re.search(r':(\d{1})$', date)
        second = second_match.group(1) if second_match else 'xx'
    else:
        second = 'xx'
    if len(second) == 1:
        second = "0" + second
    if second != "xx" and int(second) > 60:
        second = "xx"

    # 组合成标准格式,1912（清朝结束）年以前的不显示年月
    if year != "xxxx" :
        if int(year) <= 1912:
            month="xx"
            day="xx"
    formatted_date = f"{year}-{month}-{day} {hour}:{minute}:{second}"
    return formatted_date

def getEventWorker(val=None):
    query, key, dags, newQuery,clogger, retrieval_range, session_id = val
    pre_search_len = TimeLineConfig["TIMELINE_TASK_PARAMS_CONFIG"]["event_info_extract"]["longchunk_pre_search_len"] # 全文中，往前搜索的长度 配置到config
    use_longchunk = TimeLineConfig["TIMELINE_TASK_PARAMS_CONFIG"]["use_longchunk"]
    chunk = dags[query].reference[key]['description']
    all_content = dags[query].reference[key]['other_info'].get('all_content', "")

    doc_id = dags[query].reference[key]['other_info'].get('doc_id', "")
    if use_longchunk:
        if chunk in all_content:
            chunk_in_all_contentidx = all_content.find(chunk, 0)
            pre_idx = max(0, chunk_in_all_contentidx - pre_search_len)
            longChunk = all_content[pre_idx:chunk_in_all_contentidx + len(chunk)]
        else:
            # 全文中找不到chunk的话，就使用chunk
            longChunk = chunk
        use_chunk = longChunk
    else:
        use_chunk = chunk
    # 根据全文补充chunk被截断内容
    use_chunk = complete_sentence(all_content,use_chunk)
    if "publish_time" in dags[query].reference[key]['other_info']:
        publish_time = dags[query].reference[key]['other_info']['publish_time']
        if len(publish_time)<5:
            return
    else:
        return
    url = dags[query].reference[key]['url']
    chunkID = key

    chunkInfoDict = {
        'Chunk': use_chunk,
        'PublishTime': publish_time,
        'Query': query,
        "newQuery": newQuery
    }
    res, prompt = getEventExtractSub(chunkInfoDict=chunkInfoDict, newQuery=newQuery, clogger=clogger, session_id=session_id)
    tableDict = getEventExtract(res=res, chunkInfoDict=chunkInfoDict, prompt=prompt)
    standard_events = checkEvents(tableDict['Result']['Result'],url,chunkID, publish_time,doc_id, retrieval_range)
    # 只添加正确格式的事件到dag图上
    if len(standard_events)>0:
        tableDict['Result']['Result'] = standard_events
        dags.add_node_param(query, "event_info", tableDict['Result']['Result'])

def getEventInfoWithDag(dags:IGraph=None,newQuery:str=None,clogger=log,retrieval_range=None,session_id=''):
    querylist = get_dag_query_list(dags)
    querylist = sorted(querylist) #query list
    all_task = []
    reference_num = 0
    reference_list = []
    all_short_sentence_lines_origin = []
    for query in querylist:
        if hasattr(dags[query], "reference"):# 有检索结果才继续走事件抽取流程
            for key in dags[query].reference.keys():
                rerank_score=dags[query].reference[key]['rerank_score']
                #相关性分数低于0.5的不使用
                if not rerank_score or rerank_score<=0.5:
                    continue
                reference_list.append({"key": key, "description": dags[query].reference[key]['description']})
                all_short_sentence_lines_origin.append(dags[query].reference[key]['description'])
    # 动态去重阈值
    bar = dynamic_threshold(references=all_short_sentence_lines_origin)
    # 固定去重阈值
    # bar=0.8
    clogger.info("相似度去重前reference数量: {} 设定去重相似度阈值为: {} ".format(len(all_short_sentence_lines_origin), bar))
    short_sentence_inner_similarity = get_similarity(all_short_sentence_lines_origin,
                                                        all_short_sentence_lines_origin)
    _, chosen_sentences_index = find_best_unrelated_subgroup(
        all_short_sentence_lines_origin, short_sentence_inner_similarity, bar=bar
    )
    remove_dup_keys = [reference_list[index]["key"] for index in chosen_sentences_index]
    clogger.warning("相似度去重后召回结果数量:{}".format(len(remove_dup_keys)))
    run_key = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        for query in querylist:
            if hasattr(dags[query], "reference"):# 有检索结果才继续走事件抽取流程
                for key in dags[query].reference.keys():
                    if key not in remove_dup_keys:
                        continue
                    if key in run_key:
                        continue
                    run_key.append(key)
                    reference_num += 1
                    val = (query, key, dags, newQuery,clogger, retrieval_range, session_id)
                    all_task.append(executor.submit(getEventWorker, val))



if __name__ == "__main__":
    testChunk1 = {
        "Chunk": "2025年4月 在习近平主席对匈牙利进行国事访问期间，中匈双方达成多项合作共识。其中，关于布达佩斯中国文化中心启动运营的消息备受中匈各界关注。近日，总台记者走进了全新的布达佩斯中国文化中心，接下来，我们就一起来了解这个中匈文化交流的新平台。\n\n　　布达佩斯中国文化中心是根据中匈互设文化中心协定，由中国文化和旅游部在匈牙利设立的官方文化机构。在庭院中，设计人员巧妙地将苏州园林和匈牙利古典主义风格充分融合。无论是大方简洁的中式座椅、精心设置的中餐制作体验室、还是功能齐全的展览厅，都让中心所在的这座百年建筑散发出浓浓中国味。\n\n　　中国文化中心成了匈牙利的中国文化爱好者学习中文、了解中国丰富文化和旅游资源的重要平台。",
        "LongChunk": "2025年4月 在习近平主席对匈牙利进行国事访问期间，中匈双方达成多项合作共识。其中，关于布达佩斯中国文化中心启动运营的消息备受中匈各界关注。近日，总台记者走进了全新的布达佩斯中国文化中心，接下来，我们就一起来了解这个中匈文化交流的新平台。\n\n　　布达佩斯中国文化中心是根据中匈互设文化中心协定，由中国文化和旅游部在匈牙利设立的官方文化机构。在庭院中，设计人员巧妙地将苏州园林和匈牙利古典主义风格充分融合。无论是大方简洁的中式座椅、精心设置的中餐制作体验室、还是功能齐全的展览厅，都让中心所在的这座百年建筑散发出浓浓中国味。\n\n　　中国文化中心成了匈牙利的中国文化爱好者学习中文、了解中国丰富文化和旅游资源的重要平台。",
        "Article": "2025年4月 在习近平主席对匈牙利进行国事访问期间，中匈双方达成多项合作共识。其中，关于布达佩斯中国文化中心启动运营的消息备受中匈各界关注。近日，总台记者走进了全新的布达佩斯中国文化中心，接下来，我们就一起来了解这个中匈文化交流的新平台。\n\n　　布达佩斯中国文化中心是根据中匈互设文化中心协定，由中国文化和旅游部在匈牙利设立的官方文化机构。在庭院中，设计人员巧妙地将苏州园林和匈牙利古典主义风格充分融合。无论是大方简洁的中式座椅、精心设置的中餐制作体验室、还是功能齐全的展览厅，都让中心所在的这座百年建筑散发出浓浓中国味。\n\n　　中国文化中心成了匈牙利的中国文化爱好者学习中文、了解中国丰富文化和旅游资源的重要平台。\n\n　　布达佩斯中国文化中心工作人员 大卫：(匈牙利人)学习(中国)文化或者了解文化的热情很高，所以我觉得中国文化中心以后是非常重要的一个平台，让匈牙利老百姓更了解中国文化。\n\n　　中国文化中心深耕线上交流与传播，目前，中心在多个社交媒体平台，以匈中双语发布图文、视频以及互动活动。\n\n　　在中国留学的匈牙利学生李天宇，常常利用业余时间用镜头记录下自己在中国各地的旅行经历。去年4月以来，李天宇在中国文化中心推出了自己的专栏“天宇在中国”，并在海外平台积累了十多万粉丝。\n\n　　在华匈牙利留学生 李天宇：中文里面有句话就是，这个世界并不缺少美，缺少的就是能够发现美丽的眼睛。我是从一个匈牙利人的角度，能抓住或者能找到一些匈牙利人会(对中国)特别感兴趣的一些地方，所以关于中国的专栏特别成功。\n\n　　一些对中国文化充满热爱的匈牙利人，也主动加入文化中心的建设中来，义务承担了很多工作。他们认为，通过学习中国文化，可以更好了解中国和中国人。\n\n　　匈牙利匈中文化交流中心负责人 晓峰：中国书法非常漂亮，它们可以触及人类的心灵。我觉得，如果我好好学并多练习，我能更好地从心里了解中国人。\n\n　　中国文化中心负责人金浩说，中匈两国有着深厚的友谊，两国人文领域交流亮点频现，习主席访问匈牙利将为两国人文交流带来更多机遇。\n\n　　布达佩斯中国文化中心主任 金浩：我们布达佩斯中国文化中心下一步将更好地服务于中匈两国之间的人文交流，增进两国人民之间的友谊，促进民心相通。",
        "Category": "行程",
        "PublishTime": "2024-05-08 15:59",
        "Query": "这段话主要讲了什么？以及里面有哪些关键信息？"
    }

    testChunk2 = {
        "Chunk": "报道称，以军同时要求拉法城部分地区的巴勒斯坦人撤离至以方指定的“人道主义区”。\n\n　　欧洲理事会主席米歇尔11日通过社交媒体表示，以色列命令被困于拉法的平民撤离至“不安全地区”是“不可接受的”。他要求以色列政府尊重国际人道主义法，敦促其不要在拉法开展地面行动。\n\n　　米歇尔称，必须继续尽一切努力确保达成持久停火协议。欧盟致力于在“两国方案”基础上实现“公正和全面的和平”。\n\n　　据美国《华盛顿邮报》当地时间11日报道，4名熟悉美国提议的人士透露，如果以色列不全面入侵拉法，美国政府将向以色列提供援助，包括提供敏感情报，以帮助以军确定哈马斯领导人所处位置并找到哈马斯的隧道。",
        "LongChunk": "中新社北京5月12日电 综合消息：据巴勒斯坦官方通讯社“瓦法”消息，以色列方面当地时间11日空袭加沙地带多个地区，造成数十人死亡。\n\n　　报道称，加沙地带南部城市拉法多个地区当日遭遇以色列战机袭击，造成至少13人死亡。以军当日还对加沙地带中部代尔拜拉赫和扎瓦伊达等地，以及加沙地带北部加沙城发动空袭，造成至少22人死亡。\n\n　　据报道，以色列战机当日同时对加沙地带北部杰巴利耶难民营发动“地毯式轰炸”，确切死亡人数尚无法确定。\n\n　　据路透社消息，以军11日曾要求杰巴利耶地区居民与流离失所者离开，称其在注意到巴勒斯坦伊斯兰抵抗运动(哈马斯)试图重新控制该地区后，正返回该地区开展行动。\n\n　　报道称，以军同时要求拉法城部分地区的巴勒斯坦人撤离至以方指定的“人道主义区”。报道称，以军同时要求拉法城部分地区的巴勒斯坦人撤离至以方指定的“人道主义区”。\n\n　　欧洲理事会主席米歇尔11日通过社交媒体表示，以色列命令被困于拉法的平民撤离至“不安全地区”是“不可接受的”。他要求以色列政府尊重国际人道主义法，敦促其不要在拉法开展地面行动。\n\n　　米歇尔称，必须继续尽一切努力确保达成持久停火协议。欧盟致力于在“两国方案”基础上实现“公正和全面的和平”。\n\n　　据美国《华盛顿邮报》当地时间11日报道，4名熟悉美国提议的人士透露，如果以色列不全面入侵拉法，美国政府将向以色列提供援助，包括提供敏感情报，以帮助以军确定哈马斯领导人所处位置并找到哈马斯的隧道。",
        "Article": "中新社北京5月12日电 综合消息：据巴勒斯坦官方通讯社“瓦法”消息，以色列方面当地时间11日空袭加沙地带多个地区，造成数十人死亡。\n\n　　报道称，加沙地带南部城市拉法多个地区当日遭遇以色列战机袭击，造成至少13人死亡。以军当日还对加沙地带中部代尔拜拉赫和扎瓦伊达等地，以及加沙地带北部加沙城发动空袭，造成至少22人死亡。\n\n　　据报道，以色列战机当日同时对加沙地带北部杰巴利耶难民营发动“地毯式轰炸”，确切死亡人数尚无法确定。\n\n　　据路透社消息，以军11日曾要求杰巴利耶地区居民与流离失所者离开，称其在注意到巴勒斯坦伊斯兰抵抗运动(哈马斯)试图重新控制该地区后，正返回该地区开展行动。\n\n　　报道称，以军同时要求拉法城部分地区的巴勒斯坦人撤离至以方指定的“人道主义区”。\n\n　　欧洲理事会主席米歇尔11日通过社交媒体表示，以色列命令被困于拉法的平民撤离至“不安全地区”是“不可接受的”。他要求以色列政府尊重国际人道主义法，敦促其不要在拉法开展地面行动。\n\n　　米歇尔称，必须继续尽一切努力确保达成持久停火协议。欧盟致力于在“两国方案”基础上实现“公正和全面的和平”。\n\n　　据美国《华盛顿邮报》当地时间11日报道，4名熟悉美国提议的人士透露，如果以色列不全面入侵拉法，美国政府将向以色列提供援助，包括提供敏感情报，以帮助以军确定哈马斯领导人所处位置并找到哈马斯的隧道。\n\n　　另据美国有线电视新闻网报道，美国总统拜登11日表示，若哈马斯愿意释放被扣押在加沙地带的人质，“停火将从明天开始”。\n\n　　据《以色列时报》报道，抗议者11日晚在以色列多地举行示威活动，哀悼自去年10月7日新一轮巴以冲突爆发以来被杀害的人质，并要求以色列政府辞职。警方随后逮捕了3名抗议者。\n\n　　报道称，许多抗议者都是被哈马斯扣押在加沙地带的人质的家庭成员。\n\n　　另据美国有线电视新闻网消息，埃及不会与以色列就通过拉法口岸运送援助物资进行协调。埃及开罗新闻电视台11日援引一名高层消息人士的话报道称，埃及已警告以色列继续控制拉法口岸的后果，称以色列对加沙地带人道主义形势恶化负有全部责任。(完)",
        "Category": "历史冲突和事件",
        "PublishTime": "2024-05-08 15:59",
        "Query": "这段话主要讲了什么？以及里面有哪些关键信息？"
    }
    def getResult(chunk:dict=None):
        try:
            chunkInfoDict = chunk
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            print('解码格式出错')
        else:
            st = time.time()
            res, prompt = getEventExtractSub(chunkInfoDict=chunkInfoDict)
            tableDict = getEventExtract(res=res, chunkInfoDict=chunkInfoDict, prompt=prompt)
            et = time.time()
            tableDict['用时'] = '{:.5f}s'.format(et-st)
            # print(str(res)+'\n'+'用时:{:.5f}s'.format(et-st))
            from pprint import pprint
            pprint(tableDict)
    print('============testChunk1============')
    getResult(testChunk1)
    print('============testChunk2============')
    getResult(testChunk2)