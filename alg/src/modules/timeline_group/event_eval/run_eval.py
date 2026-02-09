import json
import hashlib
from tqdm import tqdm
import numpy as np
from collections import defaultdict
from  include.utils import get_similarity

def hashlib_string(input_string, algorithm='md5'):
    # 创建哈希对象
    if algorithm == 'md5':
        h = hashlib.md5()
    elif algorithm == 'sha1':
        h = hashlib.sha1()
    elif algorithm == 'sha224':
        h = hashlib.sha224()
    elif algorithm == 'sha256':
        h = hashlib.sha256()
    elif algorithm == 'sha384':
        h = hashlib.sha384()
    elif algorithm == 'sha512':
        h = hashlib.sha512()
    else:
        raise ValueError('Invalid algorithm specified')

    # 提供要哈希的字符串
    h.update(input_string.encode('utf-8'))

    # 获取哈希值
    return h.hexdigest()

def parse_one_event(event_info):
    final_event = []
    if type(event_info) == dict:
        event_info = event_info["text"][-1]
    event_info = event_info.strip()
    event_str_list = event_info.split("\n\n")
    for event_str in event_str_list:
        event_field = event_str.split("\n")
        new_field = {}
        for event in event_field:
            event = event.strip()
            if not event:
                continue
            field_name, filed_data = event.split(':', 1)
            new_field[field_name.strip()] = filed_data.strip()
        if new_field:
            final_event.append(new_field)
    return final_event

def find_most_similarity_results(label_events:list, predict_events:list, threshold:int=0.8):
    """找到与gold最相似的事件"""
    weights = {"事件标题": 0.7, "事件摘要": 0.3}
    final_results = None
    count = 0
    for field, weight in weights.items():
        event_label = [label[field] for label in label_events]
        event_predict = [label[field] for label in predict_events]
        if (not event_predict) or (not event_label):
            print("*******************这段里面获取不到相应字段*******************")
            continue
        results = get_similarity(event_predict, event_label)
        print(results)
        if not count:
            final_results = np.array(results) * weight
        else:
            final_results = final_results + np.array(results) * weight
        count +=1
    
    cols_num = np.shape(final_results)
    similarity_map = {}
    if not cols_num:
        return similarity_map
    for i in range(cols_num[1]):
        max_value = np.max(final_results)
        max_indices = np.unravel_index(np.argmax(final_results), final_results.shape)
        # 打印最大值及其位置
        print(f"Maximum value: {max_value}, at position: {max_indices}")
        
        # 将最大值及其所在行和列设置为0
        final_results[max_indices] = 0
        final_results[:, max_indices[1]] = 0
        if max_value >= threshold:
            similarity_map[max_indices] = [label_events[max_indices[1]], predict_events[max_indices[0]]]
    return similarity_map

def compute_metrics(similarity_map, predict_events):
    "比较有多少一致的，并返回预测出的结果数量"
    same_time_count = 0
    same_use_count = 0
    same_count = 0
    for k,v in similarity_map.items():
        label = v[0]
        predict = v[1]
        if predict["事件发生时间"] == label["事件发生时间"]:
            same_time_count +=1
        if predict["事件是否能用来回答新闻主题"] == label["事件是否能用来回答新闻主题"]:
            same_use_count +=1
    return same_time_count, same_use_count, len(predict_events)

def load_labels_json(data_path):
    """加载gold 数据"""
    extract_event_label = defaultdict(list)
    datalines = json.load(open(data_path))
    for dataline in datalines:
        if "textarea" not in dataline:
            continue
        text_area = dataline["textarea"]
        ref = dataline["ref"]
        id = hashlib_string(ref)
        ori_query = dataline["ori_query"]
        final_event = parse_one_event(event_info=text_area)
        extract_event_label[ori_query+ "_"+ id].extend(final_event)
    return extract_event_label

def load_predict_json(data_path):
    """加载predict 数据"""
    extract_event_label = defaultdict(list)
    datalines = json.load(open(data_path))
    for dataline in datalines:
        if "textarea" not in dataline:
            continue
        text_area = dataline["textarea"]
        ref = dataline["ref"]
        id = hashlib_string(ref)
        ori_query = dataline["ori_query"]
        final_event = parse_one_event(event_info=text_area)
        extract_event_label[ori_query+ "_"+ id].extend(final_event)
    return extract_event_label
    # extract_event_predict = defaultdict(list)
    # datalines = json.load(open(data_path))
    # for dataline in datalines:
    #     query = dataline["Query"]
    #     output = dataline["output"]["Result"]
    #     extract_event_predict[query].extend(output)
    # return extract_event_predict


def eval(labels_path, predict_path):
    extract_event_label = load_labels_json(labels_path)
    extract_event_predict = load_predict_json(predict_path)
    total_len = 0
    total_same_time_count = 0
    total_same_use_count = 0
    for query, label_events in tqdm(extract_event_label.items()):
        # 按照query相同的进行事件抽取
        predict_events = extract_event_predict[query]
        similarity_map = find_most_similarity_results(label_events=label_events, 
                                                      predict_events=predict_events)
        if not similarity_map:
            continue
        same_time_count, same_use_count, event_len = compute_metrics(similarity_map, predict_events)
        total_len += event_len
        total_same_time_count += same_time_count
        total_same_use_count += same_use_count
    print("*************相关性准确率**************", total_same_use_count/ total_len)
    print("*************时间抽取准确率**************", total_same_time_count / total_len)



if __name__ == "__main__":
    labels_path = "/Users/xxxx/Documents/workspace/GraTAG/data/qa/timeline_groudTruth.json"
    predict_path = "/Users/xxxx/Documents/workspace/GraTAG/data/qa/timeline_groudTruth.json"
    eval(labels_path, predict_path)