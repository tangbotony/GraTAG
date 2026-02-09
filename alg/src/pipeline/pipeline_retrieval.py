from concurrent.futures import ThreadPoolExecutor
from include.utils.skywalking_utils import start_sw
from include.rag.rag_recall_agent import RagRecall
from include.logger import log
import requests,json
from include.config import CommonConfig
import concurrent.futures
from tqdm import tqdm
def send_request_to_gpt4(prompt, new=True):
    #prompt=ans["prompt"]
    ## 并发版本
    if new:
        url = "xxx"
        sk = "xxx"
    else:
        url = "xxx"
        sk = "xxx"

    payload = json.dumps({
       "model": "gpt-4o",
       "messages": [{"role": "user","content": prompt}],
       "temperature": 0
    })
    headers = {
       "Authorization": "Bearer {}".format(sk),
       "Content-Type": "application/json",
    }
    res = None
    count = 0
    while count < 5:
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response = json.loads(response.text)
            res = response
            res = res["choices"][0]['message']['content']
            break
        except Exception as e:
            print('gpt4o retry:', e)
            count += 1
    if count >= 5:
        print('gpt4o error')
    return res
def queryDocCorrelation(query, doc):
    '''
    判断query与材料是否有关联
    :param query: 查询query
    :param doc: 文档
    :return: True False bool
    '''
    task_prompt_template = """你将被提供一个query和一段材料，判断材料信息是否与query有关，如果有关，则回答"true",否则返回"false"。
query: {}
材料：{}"""
    prompt = task_prompt_template.format(query, doc)
    ans = 0
    while True:
        try:
            response = send_request_to_gpt4(prompt)
            if 'true' in response or 'True' in response:
                ans = 1
            break
        except Exception as e:
                print('err:',e)
                break
    return ans

from include.context import RagQAContext
from include.utils.text_utils import get_md5
from modules.get_retrieval_range.get_retrieval_range_task import get_retrieval_range_task
from modules import *
from concurrent.futures import ThreadPoolExecutor, as_completed
import time,copy

IAAR_DataBase_config = CommonConfig['IAAR_DataBase']
search_field = {'iaar_database_kwargs': IAAR_DataBase_config['default_param']}

start_sw()
if __name__ == "__main__":
    path_query = "../data/qa/query_retrieval.txt"
    path_ans = "../data/ans/proj_999.json"
    path_ans_w_score = "../data/ans/proj_999_w_score.json"
    # True False
    switch_retrieval = True
    switch_eval = False
    switch_caculate = False

    # # step1 检索
    cnt_query = 0
    if switch_retrieval:
        eval_list = []
        query_list = []
        for query in open(path_query, "r"):
            query = query.strip()
            query_list.append(query)

        for query in query_list:
            # if '利用具体数据，描述全球新冠疫苗的接种情况' not in query:
            #     continue
            log.warning("\n\n\n #####################start retrieval {}".format(query))
            rag_querys = [query]
            semi_query = [query]


            # 嵌入时间窗
            context = RagQAContext(session_id=get_md5(query))
            context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query)
            context.set_supply_info({"is_supply": False, "supply_info": ["去年", "深圳", "北京", "大宗消费", "刚需消费"]})

            context.set_basic_user_info({"User_Date": time.time(), "User_IP": '39.99.228.188'})
            res = QueryDivisionBasedCoTTask(context).get_cot(use_scene="general", if_parallel=True, split_num_threshold=3)
            print(context.get_dag().rewrite_query)
            print(context.get_dag().origin_query)

            get_retrieval_range_task(context)
            range = context.get_retrieval_range()
            if 'keywords' in range and len(range['keywords']) > 0:
                search_field['iaar_database_kwargs']['keywords'] = ' '.join(range['keywords'])

            if 'start_time' in range and 'end_time' in range and len(range['start_time']) > 0 and len(range['end_time']) > 0:
                search_field['iaar_database_kwargs']['online_search']['start_date'] = range['start_time']
                search_field['iaar_database_kwargs']['online_search']['end_date'] = range['end_time']

            rag_recall = RagRecall(context, search_field=copy.deepcopy(search_field))
            rag_recall.router(context.get_dag().origin_query, rag_querys[0])
            rag_recall.construct_database(rag_querys, semi_query)
            data_base = rag_recall.get_data_base()
            fig_data_base = rag_recall.get_images_data_base()

            log.info("共检索到{}个材料".format(len(data_base['use_for_check_items'].keys())))
            cnt = 0
            for key, ref in data_base['use_for_check_items'].items():
                cnt += 1
                if cnt < 3:
                    log.debug("ref url:{}".format(ref['url']))
                    log.debug("ref key:【{}】, publish time:{}, description:{}".format(key,ref['other_info']['publish_time'],ref['description'].replace('\n','').replace('\r','').replace('\t','').replace(' ','')))
                tmp = {
                    "query": query, "url": ref['url'], "title": ref['title'],
                    "publish_time": ref['other_info']['publish_time'],
                    "description": ref['description'].replace('\n','').replace('\r','').replace('\t','').replace(' ',''),
                    "score": ref['other_info']['score'],
                    "rerank_score": ref['rerank_score']
                }
                eval_list.append(tmp)
            cnt_query +=1
            if cnt_query > 0:
                break
        with open(path_ans, 'w') as f:
            json.dump(eval_list, f, ensure_ascii=False)


    # ## step2 GPT4o评分
    if switch_eval:
        eval_list = json.load(open(path_ans, 'r', encoding='utf-8'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            call_lis = []
            correlation_score = []
            for record in tqdm(eval_list):
                q = record['query']
                d = record['description']
                func_call = executor.submit(queryDocCorrelation, **{"query":q,"doc":d})
                call_lis.append(func_call)

            for func_call in call_lis:
                res = func_call.result()
                correlation_score.append(res)
                llen = len(correlation_score)
                if llen%20 == 0:
                    print('len=',llen)
        for idx, record in enumerate(eval_list):
            record['eval'] = correlation_score[idx]
            del record['url']
            del record['title']
            del record['publish_time']

        with open(path_ans_w_score, 'w') as f:
            json.dump(eval_list, f, ensure_ascii=False)


    ## step3 统计
    if switch_caculate:
        eval_list = json.load(open(path_ans_w_score, 'r', encoding='utf-8'))
        ans_all = []
        ans_query = {}
        ans_all_h = []
        ans_query_h = {}
        for eval in eval_list:
            query = eval['query']
            value = eval['eval']
            value_h = value
            if 'humaneval' in eval:
                value_h = eval['humaneval']

            if query not in ans_query:
                ans_query[query] = []
                ans_query_h[query] = []
            ans_all.append(value)
            ans_all_h.append(value_h)
            ans_query[query].append(value)
            ans_query_h[query].append(value_h)

        print("总材料数量 \t相关比例 \t相关比例(h)")
        print("{} \t{:.2f} \t{:.2f}".format(len(ans_all), sum(ans_all) / len(ans_all), sum(ans_all_h) / len(ans_all_h)))

        print("\n")
        print("材料数量 \t相关比例 \t相关比例(h) \tquery, ")
        for query, ans_list in ans_query.items():
            ans_list_h = ans_query_h[query]
            print("{} \t{:.2f} \t{:.2f} \t{}".format(len(ans_list), sum(ans_list) / len(ans_list), sum(ans_list_h) / len(ans_list_h), query))

