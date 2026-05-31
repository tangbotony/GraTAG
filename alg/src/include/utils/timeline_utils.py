import  re
import json
import requests
from datetime import datetime
import traceback
from include.config import RagQAConfig,TimeLineConfig
from include.utils import get_similarity
from include.utils.Igraph_utils import ArcNode

def replace_newlines(match):
    # 在匹配的字符串中替换 \n 和 \r
    return match.group(0).replace('\n', '\\n').replace('\r', '\\r')


def clean_json_str(json_str: str) -> str:
    """
    生成的json格式可能不标准，先进行替换处理
    :param json_str:
    :return:
    """
    json_str = json_str.replace("None", "null")

    # 去除代码块符号```
    # json字符串中None换成null
    json_str = json_str.replace("None", "null")
    if "//" in json_str:
        json_str = re.sub(r'//.*?(?=\n)', '', json_str)#备用14b处理
    if ": N/A" in json_str:
        json_str = json_str.replace("N/A", '""')
    match = re.search(r'```json(.*?)```', json_str, re.DOTALL)
    if match:
        json_str = match.group(1)
    match = re.search(r'```(.*?)```', json_str, re.DOTALL)
    if match:
        json_str = match.group(1)
    # 在匹配的字符串中替换 \n 和 \r
    json_str = re.sub(r'("(?:\\.|[^"\\])*")', replace_newlines, json_str)
    # 移除键值对后面多余的逗号
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    # 修复缺少的逗号
    json_str = re.sub(r'\"\s+\"', '\",\"', json_str)
    # True、False替换
    json_str = json_str.replace("True", "true")
    json_str = json_str.replace("False", "false")
    return json_str

def compare_date(extract_date, pub_date, date_type="end"):
    if extract_date == pub_date:
        return True
    if not extract_date:
        return True
    date_list = []
    extract_date_list = extract_date.split(" ")[0].strip().split("-")
    for idx, content in enumerate(extract_date_list):
        if "x" in content and idx <=1:
            break
        elif ("x" in content) and idx >1:
            pass
        else:
            if len(content) == 1:
                content  = "0"+content
            date_list.append(content)
    date_now_list = str(datetime.now().strftime("%Y-%m-%d")).split("-")
    offset_1 = min(len(date_list), len(date_now_list))
    date_now = "-".join(date_now_list[:offset_1])
    extract_date_str =  "-".join(date_list[:offset_1])
    if not pub_date:
        return extract_date_str <= date_now

    pub_date_list = pub_date.split(" ")[0].split("-")
    offset_2 = min(len(date_list), len(pub_date_list))
    extract_date_str =  "-".join(date_list[:offset_2])
    pub_date_str = "-".join(pub_date_list[:offset_2])
    if date_type == "end":
        return extract_date_str <= pub_date_str
    return extract_date_str >= pub_date_str


def get_year_by_date(date: str):
    return "{}年".format(date[:4])


def get_season_from_date(date: str):
    assert "x" not in date[5:7]
    # TODO: 异常处理
    if date[5] == "0":
        season = "一一一二二二三三三"[eval(date[6])-1]
    else:
        season = "四"
    return "{}年第{}季度".format(date[:4], season)


def get_month_from_date(date: str):
    assert "x" not in date[5:7]
    # TODO: 异常处理
    if date[5] == "0":
        month = eval(date[6])
    else:
        month = eval(date[5:7])
    return "{}年{}月".format(date[:4], month)


def classify_by_granularity(timeline_sort_events, granularity,reference_info):
    """
    按 年，季度，月 进行事件的分类和大标题确定
    """
    if granularity == "年":
        get_title = get_year_by_date
    elif granularity == "季":
        get_title = get_season_from_date
    elif granularity == "月":
        get_title = get_month_from_date
    events = []
    current_title = get_title(timeline_sort_events[0]["事件发生时间"])
    current_event_list = []
    for each in timeline_sort_events:
        if each["chunk_id"] in reference_info:
            reference_object={
                each["chunk_id"]: {
                    "url": reference_info[each["chunk_id"]].get("url", ""),
                    "_id": reference_info[each["chunk_id"]].get("_id", ""),
                    "title": reference_info[each["chunk_id"]].get("title", ""),
                    "content": reference_info[each["chunk_id"]].get("content", ""),
                    "icon": reference_info[each["chunk_id"]].get("icon", ""),
                    "publish_time": reference_info[each["chunk_id"]].get("publish_time", ""),
                    "news_id": reference_info[each["chunk_id"]].get("news_id", ""),
                }
            }
        else:
            reference_object=""
        if get_title(each["事件发生时间"]) in current_title:
            current_event_list.append({
                "start_time": each["事件发生时间"],
                "end_time": each.get("结束时间",""),
                "img": each.get("img",""),
                "event_subject": each["事件主体"],
                "event_abstract": each["事件摘要"]+each["chunk_id"],
                "event_title": each["事件标题"],
                "reference_object": reference_object
            })
        else:
            # 开始一个新的分类大标题
            events.append({
                "title": current_title,
                "event_list": current_event_list,
            })
            current_title = get_title(each["事件发生时间"])
            current_event_list = [{
                "start_time": each["事件发生时间"],
                "end_time": each.get("结束时间",""),
                "img": each.get("img", ""),
                "event_subject": each["事件主体"],
                "event_abstract": each["事件摘要"]+each["chunk_id"],
                "event_title": each["事件标题"],
                "reference_object": reference_object
            }]
        # 注意处理最后的一组大标题类下的事件
    events.append({
        "title": current_title,
        "event_list": current_event_list,
    })
    return {
        "is_multi_subject": False,
        "events": events
    }

def extract_reference(dag, reference_threshold=0.6):
    querylist = get_dag_query_list(dag)
    reference_dict={}
    for query in querylist:
        if hasattr(dag[query], "reference"):# 有检索结果才继续走事件抽取流程
            for chunk_id,val in dag[query].reference.items():
                if val["other_info"].get("score", reference_threshold) < reference_threshold:
                    continue
                if "doc_id" not in val["other_info"]:
                    continue
                doc_id=val["other_info"].get("doc_id")
                if doc_id not in reference_dict:
                    reference_dict[doc_id] = {
                        "chunk_list": [],
                        "_id": doc_id,
                        "url": val.get("url", ""),
                        "title": val.get("title", ""),
                        "content": val['other_info'].get('all_content',""),
                        "icon": val["other_info"].get("icon", ""),
                        "news_id": val["other_info"].get("doc_id", ""),
                        "publish_time": val["other_info"].get("publish_time", ""),
                        "site": val["other_info"].get("site", ""),
                        "summary": val["other_info"].get("query_keyword", ""),
                    }
                    image_list = val["other_info"].get("images", [])
                    if isinstance(image_list, list) and len(image_list) > 0:
                        reference_dict[doc_id]["image_url_list"] = []
                        for image_item in image_list:
                            image_item_url = image_item.get("url", "")
                            if image_item_url != "" and (image_item_url not in reference_dict[doc_id]["image_url_list"]):
                                reference_dict[doc_id]["image_url_list"].append(image_item_url)
                if chunk_id not in reference_dict[doc_id]["chunk_list"]:
                    reference_dict[doc_id]["chunk_list"].append(chunk_id)

    return reference_dict

def extract_chunk_reference(dag):
    _, nodeName, _ = dag.get_turns()
    querylist = nodeName[0] #query list
    chunk_reference_dict={}
    for query in querylist:
        if hasattr(dag[query], "reference"):# 有检索结果才继续走事件抽取流程
            for chunk_id,val in dag[query].reference.items():
                if "doc_id" not in val["other_info"]:
                    continue
                doc_id = val["other_info"].get("doc_id")
                if chunk_id not in chunk_reference_dict:
                    chunk_reference_dict[chunk_id]={
                        "_id": chunk_id,
                        "news_id": doc_id,
                        "content": val.get("description", ""),
                        "icon": val["other_info"].get("icon", ""),
                        "publish_time": val["other_info"].get("publish_time", ""),
                        "title": val.get("title", ""),
                        "url": val.get("url", ""),
                    }
    return chunk_reference_dict

def search_img_by_text(params):
    event_item, candidate_images_list,used_img_url_list, log,timeout_count_list,session_id=params

    text_content = event_item["事件摘要"]
    img_url = ""
    url = RagQAConfig['FIG_CONFIG']['url']
    headers = {
       'token': 'xxx',
       'Content-Type': 'application/json',
       'Accept': '*/*',
       'Connection': 'keep-alive',
        "Authorization": "xxx"
    }
    test_input = {
        "session_id": session_id,
        "contexts": [
            {
                "type": "text",
                "content": text_content
            },

        ],
        "candidate_images": candidate_images_list,
        # 图片返回阈值
        "strategy_config": {
            "t2i_thresh": 0.20,
            "func": "time_line_insert",
        }
    }

    payload = json.dumps(test_input)
    try:
        response = requests.request("POST", url, headers=headers, data=payload,timeout=5)
        response_json_list = response.json()
        if isinstance(response_json_list,list) and response_json_list[-1]["type"] == "image":
            for img_url_item in response_json_list[-1].get("good_images",[]):
                tmp_url =img_url_item["url"]
                if tmp_url not in used_img_url_list:
                    used_img_url_list.append(tmp_url)
                    img_url = tmp_url
                    break
    except Exception as e:
        log.warning("timeline img search occur error: {}".format(traceback.format_exc()))
        timeout_count_list.append(1)

    event_item["img"] = img_url

def dynamic_threshold(references, min_threshold=0.7, max_threshold=0.95, max_length=200, min_length=20):
    """
    根据references长度设置动态的阈值
    """
    length = len(references)
    if length <= min_length:
        length = min_length
    elif length >= max_length:
        length = max_length

    threshold = min_threshold + (max_threshold - min_threshold) * (max_length - length) / (max_length - min_length)
    return threshold

def text_truncated(content, max_length=150):
    """防止模型生成超长文本"""
    truncated_text = ""
    if len(content) > max_length:
        # Find the last full stop or comma before the max length
        last_period = content.rfind('。', 0, max_length)
        last_comma = content.rfind('，', 0, max_length)
        # Determine the best position to truncate
        if last_period !=-1:
            truncated_text = content[:last_period + 1]
        else:
            truncated_text = content[:last_comma]
    else:
        truncated_text = content
    return truncated_text

def get_similarity_whitelist_query(query):
    white_query_dict = TimeLineConfig["TIMELINE_WHITE_LIST_QUERY_EXPANSION"]["expansion"]
    threshold = TimeLineConfig["TIMELINE_WHITE_LIST_QUERY_EXPANSION"]["threshold"]
    query_expansion_dict={}
    white_query_list=[]
    # 把白名单中所有问题及扩展问题放入list和dict方便后面做相似度
    for key,val in white_query_dict.items():
        white_query_list.append(key)
        white_query_list.extend(val)
        query_expansion_dict[key]=key
        for query_exp_item in val:
            query_expansion_dict[query_exp_item]=key
    # 计算用户输入query和白名单及扩展query的相似度
    cal_query_similarity=get_similarity([query],white_query_list)
    max_simi=max(cal_query_similarity[0])
    if max_simi>threshold:
        max_simi_idx = cal_query_similarity[0].index(max_simi)
        used_query=query_expansion_dict[white_query_list[max_simi_idx]]
    else:
        used_query=query
    return used_query

def get_dag_query_list(dag):
    _, nodeName, _ = dag.get_turns()
    query_list = []
    for node_item in nodeName:
        query_list.extend(node_item)
    return query_list

def cal_dif_between_ymd(pre_ymd,cur_ymd):
    #计算两个日期相差多少天
    pre_ymd=pre_ymd.replace("xx","01")
    cur_ymd=cur_ymd.replace("xx","01")
    # 定义日期格式
    if pre_ymd[0]=="-":
        pre_ymd=pre_ymd[1:]
    if cur_ymd[0]=="-":
        cur_ymd=cur_ymd[1:]
    date_format = "%Y-%m-%d"
    pre_datatime = datetime.strptime(pre_ymd, date_format)
    cur_datatime = datetime.strptime(cur_ymd, date_format)
    delta_time = cur_datatime-pre_datatime
    return abs(delta_time.days)

def split_ymd(ymd_input):
    ymd_info=ymd_input.split(" ")[0]
    bc_year=0
    if ymd_info[0] == "-":
        ymd_info=ymd_info[1:]
        bc_year=1
    ymd=ymd_info.split("-")
    if len(ymd)==3:
        cur_y, cur_m, cur_d=ymd
    elif len(ymd)==2:
        cur_y, cur_m = ymd
        cur_d="xx"
    else:
        cur_y =ymd[0]
        cur_m="xx"
        cur_d="xx"
    if bc_year:
        cur_y = "-" + cur_y
    return int(cur_y),cur_m,cur_d

# 用于补充chunk内容
def find_sentence_boundaries(text, truncated_text):
    # 找到被截断文本在原文本中的位置
    start_idx = text.find(truncated_text)
    if start_idx == -1:
        return None, None
    end_idx = start_idx + len(truncated_text)
    symbol_list = ["!", "?", "。", "！", "？", "/n", ";", "；", " "]
    # 找到前面最近的断句位置
    before_boundary = max([text.rfind(p, 0, start_idx) for p in symbol_list])
    # 找到后面最近的断句位置
    after_boundary = min([text.find(p, end_idx) for p in symbol_list if text.find(p, end_idx) != -1] or [len(text)])
    if before_boundary == -1:
        before_boundary = 0
    else:
        before_boundary += 1  # 包含断句符号本身
    if after_boundary == -1:
        after_boundary = len(text)
    else:
        after_boundary += 1  # 包含断句符号本身
    return before_boundary, after_boundary
def complete_sentence(text, truncated_text):
    before_boundary, after_boundary = find_sentence_boundaries(text, truncated_text)
    if before_boundary is not None and after_boundary is not None:
        complete_text = text[before_boundary:after_boundary].strip()
    else:
        complete_text = truncated_text
    return complete_text

def add_dag_node_ref(dag,ref,query):
    tmp_node = ArcNode(query)
    dag.add_new_node(tmp_node)
    dag.add_node_param(query, "reference", [], attr_type='list')
    dag[query].reference = ref

def add_period_if_needed(s):
    # 句末没有标点符号则添加句号
    if not s.endswith(('。', '！', '？','，','”','、')):
        return s + '。'
    else:
        return s

if __name__=="__main__":
    get_similarity_whitelist_query("姜萍事件是怎么回事")