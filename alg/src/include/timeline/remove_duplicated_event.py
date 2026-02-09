import time
import traceback
import datetime

from include.logger import log
from include.utils.Igraph_utils import IGraph, ArcNode
from include.utils import get_similarity
from include.utils.timeline_utils import search_img_by_text,get_dag_query_list,cal_dif_between_ymd,split_ymd
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from include.utils.call_fig_func import get_fig_filter
from include.config import TimeLineConfig

def add_event_img_info(events,context,log):
    reference_info = context.get_timeline_reference()
    session_id = context.get_session_id()
    request_id = context.get_request_id()
    question = context.get_question()
    start_time=time.time()
    img_list_all=[]
    all_candidate_images_set=set()
    # 最多十条请求图片
    img_insert_num=10
    for event_item in events:
        try:
            event_doc_id = event_item["doc_id"]
            event_candidate_images_list = reference_info[event_doc_id].get("image_url_list", "")
            if event_candidate_images_list != "":
                img_list_all.append(event_item)
                for event_candidate_images_url_item in event_candidate_images_list:
                    all_candidate_images_set.add(event_candidate_images_url_item)
        except Exception as e:
            log.warning(traceback.print_exc())

    # 图片池去重
    log.warning("时间线参与去重过滤的图片数：{}".format(len(all_candidate_images_set)))
    try:
        filtered_candidate_images_list, _ = get_fig_filter(text_list={
                        "session_id": session_id,
                        "request_id": request_id,
                        "question": question,
                        "candidate_images": list(all_candidate_images_set),
                        "strategy_config":
                            {"func": "time_line_insert",
                             "min_w": 250,
                             "min_h": 250,
                             # "max_w": 2048,
                             # "max_h": 1365,
                             },
                        },
                        application="timeline")
    except:
        pass
    log.warning("时间线去重过滤后的图片数：{}".format(len(filtered_candidate_images_list)))
    tmp_filed_img_list=[]
    for item in list(all_candidate_images_set):
        if item not in filtered_candidate_images_list:
            tmp_filed_img_list.append(item)

    # 选择图片去重过滤后仍然有效的事件做图片插入请求
    img_event_list_all = []
    doc_id_img_num_dict = {}  # 用于更新doc_id对应有效图片数

    for img_event_item in img_list_all:
        # 更新图片过滤后的事件中图片数目
        item_doc_id=img_event_item["doc_id"]
        event_candidate_images_list = reference_info[item_doc_id].get("image_url_list", "")
        item_img_num=0
        for tmp_url_item in event_candidate_images_list:
            if tmp_url_item in filtered_candidate_images_list:
                item_img_num+=1
        # 过滤后图片数为0，不再做图片请求
        if item_img_num==0:
            continue
        if item_doc_id not in doc_id_img_num_dict:
            doc_id_img_num_dict[item_doc_id]=1
        else:
            # 当同一doc_id出现次数>图片总数时，意味着图片都已经使用过了，不再对该事件做图片请求
            if doc_id_img_num_dict[item_doc_id]>=item_img_num:
                continue
            doc_id_img_num_dict[item_doc_id]+=1

        img_event_list_all.append(img_event_item)

    if len(img_event_list_all)<=img_insert_num:
        request_event_list=img_event_list_all
        request_num=len(request_event_list)
    else:
        request_event_list=list(np.random.choice(img_event_list_all,size=img_insert_num,replace=False))
        request_num=img_insert_num


    # 并发请求图片
    used_img_url_list=[]
    timeout_count_list=[]
    if request_num>0:
        all_task=[]
        with ThreadPoolExecutor(max_workers=request_num) as executor:
            for event_item in events:
                if event_item in request_event_list:
                    event_doc_id = event_item["doc_id"]
                    event_images_list = reference_info[event_doc_id].get("image_url_list", "")
                    event_candidate_images_list=[]
                    for event_image_item in event_images_list:
                        if event_image_item in filtered_candidate_images_list:
                            event_candidate_images_list.append(event_image_item)
                    params=(event_item,event_candidate_images_list,used_img_url_list,log,timeout_count_list,session_id)
                    all_task.append(executor.submit(search_img_by_text, params))

    end_time=time.time()
    log.warning("{}次并发请求 insert_img use time:{},采用{}张图片， 共超时失败{}次".format(len(request_event_list),round(end_time-start_time,2),len(used_img_url_list),len(timeout_count_list)))

def find_unique_events(event_list,event_similarity,threshold):
    unique_events=[]
    remove_events_idx_list=[]
    # 去重优先去掉发生晚的时间，保留早的事件
    for i, event_item in enumerate(event_list):
        # 如果当前事件已经被判断为丢弃事件则跳过
        if i in remove_events_idx_list:
            continue
        cur_event_time = event_item["事件发生时间"]
        cur_ymd, _ = cur_event_time.split(" ")
        min_idx=0
        use_flag = 1
        # 如果日期中包含x，那么则对所有事件判别去重
        if "x" in cur_ymd:
            cur_y,cur_m,cur_d=split_ymd(cur_ymd)
            # 如果月份是xx,则只针对同年份的事件做去重
            if "xx" in cur_m:
                # 从0到i，如果idx k有效，并且两者相似度>阈值,且为同一年份事件，则判断该事件为重复，丢弃该事件
                for k in range(i):
                    pre_event_time = event_list[k]["事件发生时间"]
                    pre_ymd, _ = pre_event_time.split(" ")
                    pre_y, pre_m, pre_d = split_ymd(pre_ymd)
                    if k not in remove_events_idx_list and event_similarity[i][k] > threshold:
                        use_flag = 0
                        break
                # 从i+1到-1，如果idx k有效，并且两者相似度>阈值,且为同一年份事件，则判断该事件为重复
                if use_flag:
                    for k in range(i+1,len(event_list)):
                        pre_event_time = event_list[k]["事件发生时间"]
                        pre_ymd, _ = pre_event_time.split(" ")
                        pre_y, pre_m, pre_d = split_ymd(pre_ymd)
                        if k not in remove_events_idx_list and event_similarity[i][k] > threshold:
                            # 如果k中时间包含x，则保留当前时间i，去掉k
                            if "xx" in pre_m:
                                remove_events_idx_list.append(k)
                            # 否则保留包含详细日期的事件
                            else:
                                use_flag=0
            # 如果月份不是xx，日期是xx，则只针对同月份事件做去重
            elif "xx" in cur_d:
                # 从0到i，如果idx k有效，并且两者相似度>阈值，且年月都相同，则判断该事件为重复，丢弃该事件
                for k in range(i):
                    pre_event_time = event_list[k]["事件发生时间"]
                    pre_ymd, _ = pre_event_time.split(" ")
                    pre_y, pre_m, pre_d = split_ymd(pre_ymd)
                    if k not in remove_events_idx_list and event_similarity[i][k] > threshold:
                        use_flag = 0
                        break
                # 从i+1到-1，如果idx k有效，并且两者相似度>阈值，且年月都相同，则判断该事件为重复
                if use_flag:
                    for k in range(i+1,len(event_list)):
                        pre_event_time = event_list[k]["事件发生时间"]
                        pre_ymd, _ = pre_event_time.split(" ")
                        pre_y, pre_m, pre_d = split_ymd(pre_ymd)
                        if k not in remove_events_idx_list and event_similarity[i][k] > threshold:
                            # 如果k中时间包含x，则保留当前时间i，去掉k
                            if "xx" in pre_d:
                                remove_events_idx_list.append(k)
                            # 否则保留包含详细日期的事件
                            else:
                                use_flag=0
            # 不重复则添加进unique_events
            if use_flag:
                unique_events.append(event_list[i])
            # 重复则添加idx进remove_events_idx_list
            else:
                remove_events_idx_list.append(i)
        else:
            # min_idx=0，对之前所有事件做去重
            if min_idx <= i:
                for k in range(min_idx,i):
                    # 如果idx k有效，并且两者相似度>阈值，则判断该事件为重复，丢弃该事件
                    if k not in remove_events_idx_list and event_similarity[i][k] > threshold:
                        use_flag=0
                        break
            # 不重复则添加进unique_events
            if use_flag:
                unique_events.append(event_list[i])
            # 重复则添加idx进remove_events_idx_list
            else:
                remove_events_idx_list.append(i)
    return unique_events

def get_duplicated_sort_event(dag,context,clogger=log):
    timeline_query_list = get_dag_query_list(dag)
    event_list = []
    threshold = TimeLineConfig["TIMELINE_TASK_PARAMS_CONFIG"]["event_duplicated_threshold"]
    retry_cnt = 0
    max_try_cnt = 1  # 最大尝试次数
    for timeline_query_item in timeline_query_list:
        if hasattr(dag[timeline_query_item],"event_info"):
            for event_info_item in dag[timeline_query_item].event_info:
                event_list.extend(event_info_item)
    clogger.warning("抽取出事件个数：{}".format(len(event_list)))
    # 去除标题重复事件
    event_list_title_dup_list=[]
    title_use_list=[]
    # 排序后，保证时间靠前的被留下
    event_list = sorted(event_list, key=lambda x: split_ymd(x["事件发生时间"]))
    for event_item in event_list:
        if event_item["事件标题"] not in title_use_list:
            event_list_title_dup_list.append(event_item)
            title_use_list.append(event_item["事件标题"])
    clogger.warning("去掉标题重复事件个数：{}".format(len(event_list)-len(event_list_title_dup_list)))
    event_list=event_list_title_dup_list

    # 进行事件排序和去重
    while True:
        try:
            assert len(event_list) > 0, "没有找到提取的事件"
            event_list = sorted(event_list, key=lambda x: split_ymd(x["事件发生时间"]))
            duplicated_list=[]
            for event_item in event_list:
                event_subject=event_item["事件主体"]
                event_abstract=event_item["事件摘要"]
                event_title=event_item["事件标题"]
                event_info = "新闻主体："+event_subject+"。新闻标题："+event_title+"。新闻摘要："+event_abstract
                duplicated_list.append(event_info)
            event_similarity=get_similarity(duplicated_list,duplicated_list)
            unique_events=find_unique_events(event_list,event_similarity,threshold)
            clogger.warning("去掉语义重复事件个数：{}".format(len(event_list) - len(unique_events)))
            if len(unique_events) < 2:
                unique_events = []
                clogger.warning("去重后事件数目<2，不再显示")
            if len(unique_events) > 100:
                unique_events=unique_events[-100:]
                clogger.warning("去重后事件数目>100，只显示最新的100条事件")
            # 调用相关图片检索并添加相关图片信息
            add_event_img_info(unique_events,context,clogger)
            break
        except Exception as e:
            clogger.warning(
                "get_duplicated_sort_event occurs error: {}, will retry, retry cnt:{}/{}.".format(
                    traceback.format_exc(),
                    retry_cnt,
                    max_try_cnt))
            retry_cnt += 1
            if retry_cnt >= max_try_cnt:
                clogger.warning(
                    "get_rewrite_query occurs error: {}, retry cnt:{}/{}, return {{}}.".format(e, retry_cnt,
                                                                                               max_try_cnt))
                unique_events=event_list
                break
    return unique_events


if __name__ == '__main__':
    from include.context import RagQAContext
    from include.utils.text_utils import get_md5

    test_question = "小米su7走红路线"
    # session_idx = "mock_session_0"
    # context = RagQAContext(session_id=get_md5(session_idx))
    # context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
    #                             question_id=get_md5("{}_qe".format(session_idx)), question=test_question)
    event_info2 = [{"事件发生时间": "2024-03-28 xx:xx:xx", "结束时间": "NAN", "事件主体": "小米汽车首款车型SU7",
                    "事件摘要": "2024年3月28日晚，小米汽车首款车型SU7正式上市，锁单量达到75723台。",
                    "事件标题": "小米SU7盛大上市"},
                   {"事件发生时间": "2024-03-xx xx:xx:xx", "结束时间": "2024-03-31 xx:xx:xx", "事件主体": "小米SU7订单增长",
                    "事件摘要": "2024年3月29日至31日，小米SU7订单增长极其狂暴，4分钟破万、7分钟破两万、27分钟破五万。",
                    "事件标题": "小米SU7订单狂暴增长"}]
    event_info1 = [{"事件发生时间": "2024-04-01 21:21:21", "结束时间": "NAN", "事件主体": "小米SU7上市点评",
                    "事件摘要": "2024年4月1日，小米SU7上市点评，突围20万元纯电市场。",
                    "事件标题": "小米SU7突围纯电市场点评"},
                   {"事件发生时间": "2024-04-xx xx:xx:xx", "结束时间": "NAN", "事件主体": "小米SU7营销策略",
                    "事件摘要": "2024年4月13日，小米SU7成功营销背后的策略，包括雷军的人设营销和品牌影响力增强。",
                    "事件标题": "小米SU7营销策略解析"},
                   {"事件发生时间": "2024-04-25 xx:xx:xx", "结束时间": "NAN", "事件主体": "小米SU7在北京国际车展",
                    "事件摘要": "2024年4月25日，小米SU7在北京国际车展上的发布会，宣布锁单量75723台，已交付5781台。",
                    "事件标题": "小米SU7北京车展发布亮点"}]
    dag = IGraph()
    query_1 = "小米su7初步走红"
    query_2 = "小米su7破圈"
    query_3 = "小米汽车"
    x = ArcNode(query_1)
    x2 = ArcNode(query_2)
    x3 = ArcNode(query_3)
    dag.add_new_node(x)
    dag.add_new_node(x2)
    dag.add_new_node(x3)
    dag.add_node_param(query_1, "event_info", event_info1)
    dag.add_node_param(query_2, "event_info", event_info2)
    session_idx = "mock_session_0"
    context = RagQAContext(session_id=get_md5(session_idx))
    context.add_single_question(request_id=get_md5("{}_re".format(session_idx)),
                                question_id=get_md5("{}_qe".format(session_idx)), question=test_question)
    duplicated_sort_event = get_duplicated_sort_event(dag,context)
    print("duplicated_sort_event", duplicated_sort_event)
