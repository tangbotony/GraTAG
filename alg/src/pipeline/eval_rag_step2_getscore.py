import traceback

import requests
import json
import numpy as np
from tqdm import tqdm
import os
from include.utils.timeline_utils import clean_json_str
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


key = "xxx"

PROMPT_TEMPLETE= """
你是一个评委，根据问题和标准答案对学生的答案进行打分。打分规则如下：

完全不对（0分）：
学生答案与问题无关，未展示出任何相关概念或知识。

完全正确（1分）：
学生答案准确地回答了问题，涵盖所有关键信息。
表达清晰，逻辑合理，直接且有效地回应了问题。

问题：{question}

标准答案：{correct_answer}

学生答案：{response}

回答以json格式返回，例如：
{{
    "分数": 0,
    "理由": "xxxx"
}}
"""
def send_request_to_gpt4(prompt):
    url = "xxx"
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    })
    headers = {
        "Authorization": "Bearer {}".format(key),
        "Content-Type": "application/json",
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    try:
        res_content = response.json()["choices"][0]["message"]["content"]
    except:
        res_content = "模型调用失败,response:" + str(response)

    return res_content

def call_socre(params):
    llm_res_item, save_list, score_list=params

    question = llm_res_item["question"]
    correct_answer = llm_res_item["answer"]
    llm_res_content = llm_res_item["llm_response"]
    score_prompt = PROMPT_TEMPLETE.format(question=question, correct_answer=correct_answer, response=llm_res_content)
    score_llm_output = send_request_to_gpt4(score_prompt)
    print("score_llm_output", score_llm_output)
    try:
        score_llm_output_json = json.loads(clean_json_str(score_llm_output))
        score = score_llm_output_json.get("分数", None)
        score_reason = score_llm_output_json.get("理由", None)
        llm_res_item["score_info"] = {
            "score": score,
            "score_reason": score_reason
        }
        save_list.append(llm_res_item)
        score_list.append({
            "score": score,
            "score_reason": score_reason
        })
    except:
        traceback.print_exc()


if __name__ == "__main__":
    pro_flag = True
    is_continue = False
    long_context=20000
    exp_name = "qa_exam_241111_random_choose50_memory"  # ['exam_cmmlu', 'exam_version_241104', 'qa_exam_241111_random_choose50']
    llm_response_file_path = "/Users/xxx/Documents/code/GraTAG/pipeline/pipeline_data_xxx/results/rag_eval_{}_{}.json".format(exp_name, pro_flag)
    save_path = "/Users/xxx/Documents/code/GraTAG/pipeline/pipeline_data_xxx/results/rag_eval_{}_{}_score.json".format(
        exp_name, pro_flag)
    score_path = "/Users/xxx/Documents/code/GraTAG/pipeline/pipeline_data_xxx/results/rag_eval_{}_{}_final_score.json".format(
        exp_name, pro_flag)

    with open(llm_response_file_path,'r',encoding="utf-8") as llm_file:
        llm_response_all=json.load(llm_file)
    exist_score = []
    if is_continue:
        with open(save_path,'r',encoding="utf-8") as llm_file:
            exist_score = json.load(llm_file)
    exist_question = []
    for exist_score_i in exist_score:
        exist_question.append(exist_score_i['question'])

    llm_response = []
    for llm_response_i in llm_response_all:
        if llm_response_i['question'] not in exist_question:
            llm_response.append(llm_response_i)

    save_list = []
    score_list = []
    all_task = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for llm_res_item in tqdm(llm_response):
            val = (llm_res_item, save_list, score_list)
            all_task.append(executor.submit(call_socre, val))

    save_list_total = exist_score + save_list
    with open(save_path, 'w', encoding='utf-8') as save_file:
        json.dump(save_list_total, save_file, indent=4, ensure_ascii=False)

    print("save_list", save_list_total)
    final_score = 0
    time_record_all = dict()
    for score_item in save_list_total:
        final_score += int(score_item['score_info']["score"])
        time_record_i = score_item['time_record']
        init_time = 0.0
        for key, value in time_record_i.items():
            if key != 'init_time':
                for key_time_name, value_time in value.items():
                    if key_time_name not in time_record_all:
                        time_record_all[key_time_name] = []
                    time_record_all[key_time_name].append(value_time - init_time)
                    init_time = value_time
    time_record_avg = dict()
    for key, value in time_record_all.items():
        time_record_avg[key] = np.mean(value)
    print(f"correct_num:{final_score},all_num:{len(save_list_total)},final score:",final_score/len(save_list_total))

    with open(score_path, 'w', encoding='utf-8') as save_file:
        json.dump({
            "correct_num": final_score,
            "all_num": len(save_list_total),
            "final score": final_score/len(save_list_total),
            "time": time_record_avg
        }, save_file, indent=4, ensure_ascii=False)


