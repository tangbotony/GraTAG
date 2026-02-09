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
from include.utils import clean_json_str, classify_by_granularity
import copy
from include.utils.timeline_utils import split_ymd,add_period_if_needed

trans_map = {"start_time": "事件发生时间", "end_time": "结束时间", "event_subject": "事件主体",
             "event_abstract": "事件摘要", "event_title": "事件标题"}
granularity_list = ["年", "季", "月", "周", "日"]


def get_events_granularity(timeline_sort_events):
    """
    获取提取事件列表的时间粒度信息，可能的返回值为“年”“月”“日”
    """
    events_granularity = "日"
    for each in timeline_sort_events:
        if "x" in each["事件发生时间"][8:10]:  # 日期为x，应设置粒度为月
            if "x" in each["事件发生时间"][5:7]:
                return "年"
            events_granularity = "月"
    return events_granularity

def title_postprocess(timeline_dict,event_num):
    title_num=len(timeline_dict["events"])
    # 如果只有单个标题不显示
    if title_num==1:
        timeline_dict["events"][0]["title"]=""
    # 如果2/3的事件都是单独标题，则不显示标题
    elif title_num >= (event_num*2)/3 and timeline_dict["is_multi_subject"] == False:
        tmp_highlight_event_dict= {"title":"","event_list":[]}
        for title_item in timeline_dict["events"]:
            tmp_highlight_event_dict["event_list"].extend(title_item["event_list"])
        timeline_dict["events"] = [tmp_highlight_event_dict]
    else:
        timeline_dict["events"]=sorted(timeline_dict["events"], key=lambda x: split_ymd(x["event_list"][-1]["start_time"]))

def check_event_num(timeline_dict):
    event_num=0
    for title_item in timeline_dict["events"]:
        event_num+=len(title_item["event_list"])
    return event_num

def check_time_format(event_list,start_time_key):
    for sub_event_item in event_list:
        if start_time_key in sub_event_item:
            # 对于公元前的时间单独处理
            if sub_event_item[start_time_key].count("-")==3 and sub_event_item[start_time_key][0]=="-":
                sub_event_item[start_time_key] = sub_event_item[start_time_key][:5]+sub_event_item[start_time_key][5:].replace("-00", "")
            else:
                sub_event_item[start_time_key] = sub_event_item[start_time_key].replace("-00","")
            # 去除日期中无效的xx
            sub_event_item[start_time_key] = sub_event_item[start_time_key].replace("-xx","")
            # 去除时间中无效的xx及无效时间
            sub_event_item[start_time_key] = sub_event_item[start_time_key].replace("xx:xx:xx", "")
            sub_event_item[start_time_key] = sub_event_item[start_time_key].replace(":xx", "")
            sub_event_item[start_time_key] = sub_event_item[start_time_key].replace("00:00:00", "")
            sub_event_item[start_time_key] = sub_event_item[start_time_key].replace("23:59:59", "")

def get_highlight_events(timeline_sort_events, reference_info,granularity,
                         model_name=TimeLineConfig["TIMELINE_TASK_MODEL_CONFIG"]["hightlight_extract"], clogger=log, session_id=''):
    highlight_event_dict = {"is_multi_subject": False, "events": []}
    if len(timeline_sort_events)<=1:
        return highlight_event_dict
    if granularity:
        events_granularity = get_events_granularity(timeline_sort_events)
        if granularity_list.index(events_granularity) <= granularity_list.index(granularity) or granularity == "周":
            # 当提取出的时间粒度大于等于用户所要求的时间粒度时，无视用户要求并视为和提取出的事件时间粒度一致
            # 此时分类大标题的拟定由LLM完成（即直接进入else分支）
            granularity = None
            highlight_event_dict = get_highlight_events(timeline_sort_events,reference_info,granularity, session_id=session_id)
        else:
            # 当提取出的时间粒度小于用户所要求的时间粒度时，分类大标题的拟定参考用户指定的时间粒度
            highlight_event_dict = classify_by_granularity(timeline_sort_events, granularity,reference_info)
            # 后处理时间格式
            for event_list in highlight_event_dict["events"]:
                sub_events=event_list["event_list"]
                check_time_format(sub_events,"start_time")


    else:

        retry_cnt = 0
        max_try_cnt = 1  # 最大尝试次数
        event_dict = {}
        query_event_list=[]
        # 不需要输入highlight提取prompt中的信息
        keys_to_remove = ["url", "chunk_id","img","doc_id","事件是否是新闻主题的时间线内容"]
        check_time_format(timeline_sort_events,"事件发生时间")
        # 为每个事件添加idx，构建idx和对应事件的字典
        for idx, item in enumerate(timeline_sort_events):
            item["序号"] = idx
            event_dict[str(idx)] = {}
            # 构建事件信息映射
            trans_map = {"start_time": "事件发生时间", "event_subject": "事件主体",
                         "event_abstract": "事件摘要", "event_title": "事件标题","img":"img"}
            reference_key=["url","_id","title","content","icon","publish_time","news_id"]
            for key, val in trans_map.items():
                if val in item:
                    if val=="事件摘要":
                        # 末尾没有标点符号则添加句号
                        item[val]=add_period_if_needed(item[val])
                        # 拼接chunkid，方便挂载引证
                        event_dict[str(idx)][key] = item[val]+item["chunk_id"]
                    else:
                        event_dict[str(idx)][key] = item[val]
            #组装reference字段内容
            event_dict[str(idx)]["reference_object"] = {item["chunk_id"]: {}}
            if item["chunk_id"] in reference_info:
                for reference_item in reference_key:
                    event_dict[str(idx)]["reference_object"][item["chunk_id"]][reference_item]=reference_info[item["chunk_id"]].get(reference_item,"")
            query_event_list.append({k: v for k, v in item.items() if k not in keys_to_remove})

        task_prompt_template = PromptConfig["timeline_highlight_extract_without_granularity"]["QWEN_input_item"]


        query = task_prompt_template.format(num_0 = len(query_event_list)-1, num_1 = len(query_event_list), num_2 = len(query_event_list),num_3=len(query_event_list)//3, input = str(query_event_list))
        clogger.warning("正在对{}条事件进行highlight提取".format(len(query_event_list)))

        # 进行事件highlight提取
        while True:
            try:
                assert len(timeline_sort_events) > 0, "没有找到提取的事件"
                response_ori = llm_call(query=query, model_name=model_name, clogger=clogger)
                response = json.loads(clean_json_str(response_ori))
                assert isinstance(response, dict), "时间线标题总结模型输出格式不符合预期"
                assert "事件主题是否是历史战争冲突或者娱乐新闻" in response, "事件主体判断缺少"
                assert "是否多事件主体展示" in response, "多主体判断缺少"
                assert "事件集合" in response, "highlight提取结果缺少"
                if response["事件主题是否是历史战争冲突或者娱乐新闻"] == "是" and response["是否多事件主体展示"] == "是":
                    # 暂时关闭多主体，后面再优化
                    highlight_event_dict["is_multi_subject"] = False
                else:
                    highlight_event_dict["is_multi_subject"] = False
                # 从返回结果的idx查询对应的事件
                use_idx_list=[]
                for extract_item in response["事件集合"]:
                    tmp_event_list = []
                    tmp_tile = extract_item["标题"]
                    event_idx_dict_list = extract_item["事件序号"]
                    for item in event_idx_dict_list:
                        # 保证每个事件只出现一次
                        if str(item) not in use_idx_list and str(item) in event_dict:
                            use_idx_list.append(str(item))
                            tmp_event_list.append(event_dict[str(item)])
                    # 保证标题下有事件
                    if len(tmp_event_list)>0:
                        # 增加排序，确保结果正序排列
                        tmp_event_list = sorted(tmp_event_list, key=lambda x: split_ymd(x["start_time"]))
                        tmp_save_event_dict = {"title": tmp_tile, "event_list": tmp_event_list}
                        highlight_event_dict["events"].append(tmp_save_event_dict)
                not_multi_subject=copy.deepcopy(highlight_event_dict)
                # 多主体逻辑，一个事件主体下面一个事件
                if highlight_event_dict["is_multi_subject"]:
                    event_extract_list = []
                    for idx in range(len(event_dict)):
                        multi_subject_save_dict={"title": event_dict[str(idx)]["event_subject"], "event_list": [event_dict[str(idx)]]}
                        event_extract_list.append(multi_subject_save_dict)
                    event_extract_list = sorted(event_extract_list, key=lambda x: split_ymd(x["event_list"][0]["start_time"]))
                    highlight_event_dict["events"]=event_extract_list
                    # 主体间相似度匹配
                    threshold = 0.8
                    subject_list = [item["title"] for item in highlight_event_dict["events"]]
                    subject_list_similarity = get_similarity(subject_list, subject_list)
                    unique_subject_dict={}
                    for i, event_item in enumerate(subject_list):
                        if i==0:
                            unique_subject_dict[subject_list[i]] = 1
                        for j in range(i):
                            if subject_list_similarity[i][j] >= threshold:
                                subject_list[i] = subject_list[j]
                                # 相似的主体使用同一主体名称
                                highlight_event_dict["events"][i]["title"] = subject_list[i]
                                if subject_list[i] not in unique_subject_dict:
                                    unique_subject_dict[subject_list[i]] = 1
                                else:
                                    unique_subject_dict[subject_list[i]] += 1
                                break
                    unique_subject_dict_max_time=max(unique_subject_dict.values())
                    # 当主体数量小于3并且最多主体出现次数很多时，不走多主体
                    if len(unique_subject_dict)<3 or unique_subject_dict_max_time>len(subject_list)-len(unique_subject_dict):
                        highlight_event_dict = not_multi_subject
                        highlight_event_dict["is_multi_subject"] = False
                assert check_event_num(highlight_event_dict)>1, "highlight提取后事件数目不足两条"

                break
            except Exception as e:
                clogger.warning(
                    "get_highlight_events occurs error: {}, will retry, retry cnt:{}/{}.".format(
                        traceback.format_exc(),
                        retry_cnt,
                        max_try_cnt))
                retry_cnt += 1
                if retry_cnt >= max_try_cnt:
                    clogger.warning(
                        "get_highlight_events occurs error: {}, retry cnt:{}/{}, return {{}}.".format(e, retry_cnt,
                                                                                                   max_try_cnt))
                    show_events=[]
                    # 重置highlight内容
                    highlight_event_dict["events"]=[]
                    for idx in range(len(timeline_sort_events)):
                        show_events.append(event_dict[str(idx)])
                    tmp_save_event_dict = {"title": "", "event_list": show_events}
                    highlight_event_dict["events"].append(tmp_save_event_dict)
                    break
    event_show_num=check_event_num(highlight_event_dict)
    title_postprocess(highlight_event_dict,event_show_num)
    clogger.warning("最终展示事件个数：{}".format(event_show_num))
    return highlight_event_dict


if __name__ == "__main__":
    test_timeline_sort_events_str = (
        '[{"事件发生时间": "1986-07-10", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国正式提出恢复其在关贸总协定（GATT，WTO的前身）中的缔约国地位的申请。", "事件标题": "中国提出恢复GATT缔约国申请","url":"www.xxxxxxx.com","chunk_id":"123"},'
        '{"事件发生时间": "1987-10-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国开始与GATT缔约方进行非正式的双边磋商。", "事件标题": "中国与GATT缔约方开始双边磋商","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1989-05-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "由于政治原因，中国加入GATT的谈判进程暂时放缓。", "事件标题": "政治原因导致GATT谈判放缓","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1992-10-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国改革开放政策推动下，中国政府加快了加入GATT的准备工作。", "事件标题": "中国加快加入GATT准备工作","url":"www.xxxxxxx.com","chunk_id":"123"},'
        '{"事件发生时间": "1994-02-xx", "结束时间": "NAN", "事件主体": "GATT", "核心人物": "无", "地点": "无", "事件摘要": "在乌拉圭回合谈判结束时，GATT转变为WTO，中国的谈判对象由GATT转变为WTO。", "事件标题": "乌拉圭回合后GATT转变为WTO","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1995-07-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国与WTO开始正式的双边谈判。", "事件标题": "中国与WTO开始双边谈判","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1997-08-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国与新西兰达成了第一个双边市场准入协议。", "事件标题": "中国与新西兰达成市场准入协议","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "1999-11-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "美国和中国就中国加入WTO的条款达成了双边协议，这是中国入世谈判中最重要的双边协议之一。", "事件标题": "中国与美国达成入世双边协议","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2000-05-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "欧盟与中国就中国加入WTO的双边市场准入问题达成一致。", "事件标题": "中国与欧盟达成市场准入一致","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2000-10-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国与加拿大就中国加入WTO达成双边协议。", "事件标题": "中国与加拿大达成入世双边协议","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-06-xx", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国最终完成了与墨西哥的双边市场准入谈判。", "事件标题": "中国与墨西哥完成市场准入谈判","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-09-13", "结束时间": "NAN", "事件主体": "世贸组织中国工作组", "核心人物": "无", "地点": "布鲁塞尔", "事件摘要": "世贸组织中国工作组第18次会议在布鲁塞尔举行，通过了中国加入世贸组织议定书及附件和中国工作组报告书。", "事件标题": "世贸组织中国工作组通过入世议定书","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-11-10", "结束时间": "NAN", "事件主体": "世贸组织", "核心人物": "无", "地点": "多哈", "事件摘要": "在多哈举行的世贸组织第四届部长级会议上，会议审议并通过了中国加入世贸组织的决定。", "事件标题": "世贸组织部长级会议通过中国入世","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-11-11", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国代表签署了中国加入世贸组织议定书。", "事件标题": "中国签署入世议定书","url":"www.xxxxxxx.com","chunk_id":"123"}, '
        '{"事件发生时间": "2001-12-11", "结束时间": "NAN", "事件主体": "中国", "核心人物": "无", "地点": "无", "事件摘要": "中国正式成为WTO的第143个成员。", "事件标题": "中国正式成为WTO成员","url":"www.xxxxxxx.com","chunk_id":"123"}]')
    test_timeline_sort_events = json.loads(test_timeline_sort_events_str)
    # 无时间粒度信息
    highlight_res = get_highlight_events(test_timeline_sort_events,"", granularity=None)
    print("无时间粒度信息",highlight_res)
    # 有时间粒度信息
    highlight_res = get_highlight_events(test_timeline_sort_events, "",granularity="年")
    print("有时间粒度信息",highlight_res)
