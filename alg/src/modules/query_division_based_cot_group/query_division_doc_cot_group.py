import traceback
import hashlib
from string import Template
import mongoengine as me
import re
import random
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.context import DocQAContext, RagQAReturnCode
from include.logger import ContextLogger
from include.utils.mongo_utils import PdfOutlineResult,UploadDocument
import json
import time
from include.config import ModuleConfig
from modules.query_division_based_cot_group.judge_complexity import MultiHopSplitQueries
from include.utils import llm_call
from include.decorator import timer_decorator
from include.utils.Igraph_utils import construct_dag
from include.utils.multiprocess_utils import pool_async
from include.utils import get_similarity, minhash_filter_repeat, similarity_filter_list


class QueryDivisionDocCoTTask():
    """
    QA流程中调用DOC_COT类，从预处理的PDF解析思维链问题中做去重，并与用户输入做相似度对比筛选，取前十。
    """
    def __init__(self, context:DocQAContext):
        self.context = context
        self.log = ContextLogger(self.context)
        self.log.info("callDocCOTTask")
        self.query = self.context.get_question()

    @timer_decorator
    def get_cot(self, **kwargs):
        try:
            pro_flag = kwargs.get("pro_flag", True)
            beginning_time = time.time()
            query_type = self.context.get_doc_query_type()
            self.log.info(f"用户输入的question为{self.query}，是一个{query_type}问题")
            if pro_flag:
                if query_type == "综述问题":
                    self.get_doc_cot()
                elif query_type == "具体问题":
                    self.get_query_doc_cot()
                else:
                    raise Exception(f"query_type is not valid. Type:{query_type} ")
            else:
                dag = construct_dag('')
                dag.origin_query = self.context.get_origin_question()
                self.context.set_dag(dag)
            dag = self.context.get_dag()
            node_turn, query_turn, final = dag.get_turns()
            self.log.info(f"用户输入的question为{self.query}，拆分&匹配pre_cot结果:{query_turn}")
            
            # return
            is_success = True
            return_code = RagQAReturnCode.FUNCTION_RUN_SUCCESS
            error_detail = {}
            err_msg = ""
            self.log.info(
                "doc_query_cot success, use time {}s".format(round(time.time() - beginning_time, 2)))
        except Exception as e:
                self.log.error(traceback.format_exc())
                is_success = False
                return_code = RagQAReturnCode.UNKNOWN_ERROR
                error_detail = {"exc_info": str(sys.exc_info()), "format_exc": str(traceback.format_exc())}
                err_msg = str(e)

        return json.dumps({"is_success": is_success,
                           "return_code": return_code,
                           "detail": error_detail,
                           "timestamp": str(time.time()),
                           "err_msg": err_msg
                           }, ensure_ascii=False)

    def get_query_doc_cot(self):
        multihop_dict = MultiHopSplitQueries(self.context).get_multi_hop_queries()
        sub_questions = multihop_dict["sub_questions"]

        # 根据oss_id从cot池取信息
        oss_ids = self.context.get_pdf_ids()
        oss_ids = oss_ids if isinstance(oss_ids, list) else [oss_ids]
        pdf_queries, figtables_info = self.extract_precot_data(oss_ids)

        # 将图表的信息与当前question关联，去相关度高的info整个存到context
        figtables_tmp_dic, figtables_tmp_cots = {}, []
        for fig_caption in figtables_info:
            for cot_res in fig_caption.pre_cot:
                if cot_res: 
                    figtables_tmp_dic[cot_res] = fig_caption
                    figtables_tmp_cots.append(cot_res)
        score_list = get_similarity(figtables_tmp_cots, [self.query])
        fig_cot_lis = [figtables_tmp_cots[i] for i in range(len(figtables_tmp_cots)) if score_list[i][0] > 0.7] 
        figtables_info_related = [figtables_tmp_dic[cot_res] for cot_res in fig_cot_lis]
        figtables_info_related = list(set(figtables_info_related))     # [PdfOutlineResult, PdfOutlineResult...]
        self.context.set_related_figtable(figtables_info_related[:20])
        self.log.info(f"文档所有的图表有 {len(figtables_info)} 个，与query相关的图表信息召回个数为 {len(figtables_info_related)}个。")

        # 非图表title的COT去重且相关query的信息取前十。
        if pdf_queries == []:
            self.log.warning(f"预处理的文档COT结果没有取到！oss_ids: {oss_ids}")
        else:
            self.log.warning(f"预处理的文档COT: {pdf_queries}")   # 运航采用，稳定后可删除
        latent_cot_list = pdf_queries
        latent_cot_list = minhash_filter_repeat(latent_cot_list)
        score_list = get_similarity(latent_cot_list, [self.query])
        doc_cot_list = [latent_cot_list[i] for i in range(len(latent_cot_list)) if score_list[i][0] > 0.5][:10]   

        # 构建doccontext的dag
        doc_cot_list += sub_questions
        dag = construct_dag(doc_cot_list)
        dag.origin_query = self.context.get_origin_question()
        self.context.set_dag(dag)

    def get_doc_cot(self):
        oss_ids = self.context.get_pdf_ids()
        pdf_queries, figtables_info = self.extract_precot_data(oss_ids)
        
        # 图表信息做相似度筛选，存储图表的信息到context
        random.shuffle(figtables_info)
        self.context.set_related_figtable(figtables_info[:20])
        self.log.info(f"从文档中的图表信息中随机选取 {len(figtables_info)} 个。")

        # 非图表title的COT去重随机取前十。
        if pdf_queries == []:
            self.log.warning(f"预处理的文档COT结果没有取到！oss_ids: {oss_ids}")
        else:
            self.log.warning(f"预处理的文档COT: {pdf_queries}")
        latent_cot_list = pdf_queries
        latent_cot_list = minhash_filter_repeat(latent_cot_list)[:30]
        doc_cot_list = similarity_filter_list(latent_cot_list, threshold=0.85)[:10]

        # 构建doccontext的dag
        dag = construct_dag(doc_cot_list)
        dag.origin_query = self.context.get_origin_question()
        self.context.set_dag(dag)

    def extract_precot_data(self, oss_ids):
        # 调用doc预COT的结果，返回title-cot和图表-cot两个列表
        if isinstance(oss_ids, str): oss_ids = [oss_ids]
        pdf_queries = []
        figtables_info = []
        try:
            for cot_oss_id in oss_ids:
                pdf_cot_res_all = extract_mongo_data(cot_oss_id)
                pdf_cot_res = [item.pre_cot for item in pdf_cot_res_all if item.pre_cot != None and item.type == "title"]  # [[xxx, xxx, xxx], [], ...]
                tmp_figtables_info = [item for item in pdf_cot_res_all if item.type in ["table_caption", "figure_caption"]] # [PdfOutlineResult, PdfOutlineResult...]
                figtables_info.extend(tmp_figtables_info)
                for cot_list in pdf_cot_res:
                    pdf_queries.extend(cot_list)
            self.log.info(f"从mongodb中取出数据{len(pdf_queries)}条")
        except:
            traceback.print_exc()
            pass
        return pdf_queries, figtables_info



class DocPreCOT:
    """
    QA流程中调用DOC_PRE_COT类，预处理的PDF解析思维链问题，并储存。
    """
    def __init__(self):
        self.log = ContextLogger()
        self.log.info("callDocPreCOTTask")


    @timer_decorator
    def pre_doc_cot(self, doc_id, oss_id, raw_outline_list):
        # 从mongodb取出pdf解析后的outline数据
        if isinstance(raw_outline_list, list):
            input_dict_list = raw_outline_list
        else:
            input_dict_list = raw_outline_list.get("data", None)
        if not input_dict_list or input_dict_list == []:
            raise Exception("传入raw_outline_list数据为空。")
        input_dict_list = filter_repeat(input_dict_list)
        input_dict_list = [{**item, "_id": get_hash_id(item, oss_id)} for item in input_dict_list]
        
        beginning_time = time.time()
        finished_id_list = []
        # 全量输入，去重处理过的内容，并做筛选
        # mongodb更新方式非增量，本去重方法不启用：
        # former_cot_res = extract_mongo_data(oss_id=cot_oss_id)
        # finished_id_list = [cot_item["_id"] for cot_item in former_cot_res]
        input_dict_list = [item for item in input_dict_list if item["_id"] not in finished_id_list]
        input_dict_list = [item for item in input_dict_list if len(item["text"]) > 5]
        if input_dict_list == []:
            return 
        if ModuleConfig.doc_cot_config.doc_cot_method == "each_step":
            res_cot_dic = self.pre_cot_by_each_step(input_dict_list)
        elif ModuleConfig.doc_cot_config.doc_cot_method == "parallel_call":   # qwen系列推荐
            res_cot_dic = self.pre_cot_by_parallel_call(input_dict_list, parallel_batch_size =  ModuleConfig.doc_cot_config.parallel_call_bs)
        elif ModuleConfig.doc_cot_config.doc_cot_method == "one_rush_shorter_input":
            res_cot_dic = self.pre_cot_by_one_rush(input_dict_list, prompt_length = ModuleConfig.doc_cot_config.one_rush_prompt_length)
        else:
            res_cot_dic = self.pre_cot_by_one_rush(input_dict_list)       # GPT系列推荐

        for i in range(len(input_dict_list)):
            input_dict_list[i]["oss_id"] = oss_id
            _id = input_dict_list[i]["_id"]
            pre_cot = res_cot_dic.get(_id, None)
            queries_list = clean_cot_list(pre_cot)
            input_dict_list[i]["pre_cot"] = queries_list
        
        self.log.info(f"pdf预解析完成，最终处理得到数据{len(list(res_cot_dic.keys()))}/{len(input_dict_list)}条，用时{time.time()-beginning_time}")
        if input_dict_list != []:
            insert_mongodb(oss_id, input_dict_list)       # TODO 上线解注释
            update_precot_flag(doc_id) # 更新pre_cot完成标志位


    def pre_cot_by_each_step(self, input_dict_list):
        # 导入模板
        DocTitleCOTTemplate = ModuleConfig["DocTitleCOTTemplate"]
        DocTextCOTTemplate = ModuleConfig["DocTextCOTTemplate"]
        DocTableFigCOTTemplate = ModuleConfig["DocTableFigCOTTemplate"]

        prompt_list = []
        for info_dict in input_dict_list:
            assert info_dict["type"] in ["title", "figure_caption", "table_caption", "text"] 
            if info_dict["type"] == "title":
                prompt = Template(DocTitleCOTTemplate).substitute({"title_info": info_dict["text"]})
            elif info_dict["type"] in ["figure_caption", "table_caption"]:
                prompt = Template(DocTableFigCOTTemplate).substitute({"table_figure_info": info_dict["text"]})
            else:
                prompt = Template(DocTextCOTTemplate).substitute({"text_info": info_dict["text"]})
            prompt_list.append(info_dict["_id"] + "\t" + prompt)

        def call_llm(prefixed_prompt):
            _id, input_prompt = prefixed_prompt.split("\t")
            response = llm_call(input_prompt, model_name=ModuleConfig.doc_model_name,temperature = 0.0, n = 1, max_tokens=128)
            if "无法生成" in str(response):
                return _id, None 
            else:
                return _id, response
        res_cot_list = pool_async(call_llm, prompt_list)
        res_cot_dic = {k:v for (k, v) in res_cot_list}
        return res_cot_dic

    def pre_cot_by_parallel_call(self, input_dict_list, parallel_batch_size = 30):
        # 导入模板
        DocTitleCOTTemplate = ModuleConfig["DocTitleCOTTemplate"]
        DocTextCOTTemplate = ModuleConfig["DocTextCOTTemplate"]
        DocTableFigCOTTemplate = ModuleConfig["DocTableFigCOTTemplate"]

        id_list = []
        prompt_list = []
        for info_dict in input_dict_list:
            assert info_dict["type"] in ["title", "figure_caption", "table_caption", "text"] 
            if info_dict["type"] == "title":
                prompt = Template(DocTitleCOTTemplate).substitute({"title_info": info_dict["text"]})
            elif info_dict["type"] in ["figure_caption", "table_caption"]:
                prompt = Template(DocTableFigCOTTemplate).substitute({"table_figure_info": info_dict["text"]})
            else:
                prompt = Template(DocTextCOTTemplate).substitute({"text_info": info_dict["text"]})
            id_list.append(info_dict["_id"])
            prompt_list.append(prompt)
        ids_batches = [id_list[i:i + parallel_batch_size] for i in range(0, len(id_list), parallel_batch_size)]
        prompts_batches = [prompt_list[i:i + parallel_batch_size] for i in range(0, len(prompt_list), parallel_batch_size)]
    
        def call_llm(ids_batch, prompts_batch):
            responses = llm_call(prompts_batch, is_parallel = True, model_name=ModuleConfig.doc_model_name,temperature = 0.0, n = 1, max_tokens=128)
            responses_dict = {}
            for (id_, ans) in zip(ids_batch, responses):
                if "无法生成" in str(ans):
                    responses_dict[id_] = None
                else:
                    responses_dict[id_] = ans
            return responses_dict
        res_cot_dicts = pool_async(call_llm, ids_batches, prompts_batches)

        final_dict = {}
        for d in res_cot_dicts:
            final_dict.update(d)

        return final_dict


    def pre_cot_by_one_rush(self, input_dict_list, prompt_length = 10000):
        # 导入模板
        DocTableFigCOTOneRushTemplate = ModuleConfig["DocTableFigCOTOneRushTemplate"]
        DocTitleCOTOneRushTemplate = ModuleConfig["DocTitleCOTOneRushTemplate"]
        DocTextCOTOneRushTemplate = ModuleConfig["DocTextCOTOneRushTemplate"]

        title_lis, title_ids_lis = [], []
        text_lis, text_ids_lis = [], []
        figure_table_lis, figuretable_ids_lis = [], []
        for info_dict in input_dict_list:
            if info_dict["type"] in ["figure_caption", "table_caption"]:
                figure_table_lis.append(f"case{len(figure_table_lis) + 1}:" + info_dict["text"] + "。")
                figuretable_ids_lis.append(info_dict["_id"])
            elif info_dict["type"] in ["title"]:
                title_lis.append(f"case{len(title_lis) + 1}:" + info_dict["text"] + "。")
                title_ids_lis.append(info_dict["_id"])
            else:
                text_lis.append(f"case{len(title_lis) + 1}:" + info_dict["text"] + "。")
                text_ids_lis.append(info_dict["_id"])
        
        prompt_lis = []
        case_lis = []
        if figure_table_lis:
            figure_table_info = "\n".join(figure_table_lis)
            prompt = Template(DocTableFigCOTOneRushTemplate).substitute({"title_info": figure_table_info})
            prompt_lis.append(prompt)
            case_lis.append(figuretable_ids_lis)
        if title_lis:
            # 一般title类的信息比较多，防止单个prompt长度过长，对其做分组合成多个prompts
            grouped_title_lis = [title_lis[i:i + prompt_length] for i in range(0, len(title_lis), prompt_length)]
            grouped_case_lis = [title_ids_lis[i:i + prompt_length] for i in range(0, len(title_ids_lis), prompt_length)]
            for each_group_title, each_group_ids in zip(grouped_title_lis, grouped_case_lis):
                title_info = "\n".join(each_group_title)
                prompt = Template(DocTitleCOTOneRushTemplate).substitute({"title_info": title_info})
                prompt_lis.append(prompt)
                case_lis.append(each_group_ids)
        if text_lis:
            text_info = "\n".join(text_lis)
            prompt = Template(DocTextCOTOneRushTemplate).substitute({"title_info": text_info})
            prompt_lis.append(prompt)
            case_lis.append(text_ids_lis)

        # # 多进程调用
        def call_llm(onrush_prompt, cases):
            response = llm_call(onrush_prompt, model_name=ModuleConfig.doc_model_name,temperature = 0.0, n = 1, max_tokens=1280)
            cases_answers = response.split("<div>")
            cases_answers = [item.replace("```json", "").replace("```", "").strip() for item in cases_answers]
            cases_answers = [item for item in cases_answers if item != ""]
            cot_final = []
            for i, case_answer in enumerate(cases_answers):            
                if "无法生成" in case_answer:
                    cot_final.append([cases[i], None])
                else:
                    try:
                        tmp_answer = eval(case_answer)
                        tmp_answer = "\n".join(list(tmp_answer.values())[0])
                        cot_final.append([cases[i], tmp_answer])
                    except:
                        cot_final.append([cases[i], None])
            return cot_final
        several_rush_finals = pool_async(call_llm, prompt_lis, case_lis) 
        res_cot_list = [item for sublist in several_rush_finals for item in sublist]
        res_cot_dic = {k:v for (k, v) in res_cot_list}
        return res_cot_dic

        # # 批调用
        # responses = llm_call(prompt_lis, is_parallel = True, model_name=ModuleConfig.doc_model_name,temperature = 0.0, n = 1, max_tokens=1280)
        # res_cot_dic = {}
        # for response, each_case_lis in zip(responses, case_lis):
        #     cases_answers = response.split("<div>")
        #     cases_answers = [item.replace("```json", "").replace("```", "").strip() for item in cases_answers]
        #     cases_answers = [item for item in cases_answers if item != ""]
        #     for i, case_answer in enumerate(cases_answers):            
        #         if "无法生成" in case_answer:
        #             res_cot_dic[each_case_lis[i]] = None
        #         else:
        #             try:
        #                 tmp_answer = eval(case_answer)
        #                 tmp_answer = "\n".join(list(tmp_answer.values())[0])
        #                 res_cot_dic[each_case_lis[i]] = tmp_answer
        #             except:
        #                 res_cot_dic[each_case_lis[i]] = None
        # return res_cot_dic


def filter_repeat(raw_dic_list):
    clean_dic_list = []
    tmp_record = []
    for dic in raw_dic_list:
        if dic["text"] not in tmp_record:
            tmp_record.append(dic["text"]) 
            clean_dic_list.append(dic)
    return clean_dic_list

def update_precot_flag(doc_id):
    uploadDocument = UploadDocument.objects(_id=doc_id).first()
    uploadDocument.pre_cot = True
    uploadDocument.save()

def clean_cot_list(pre_cot_str):
    """删除编号"""
    if not pre_cot_str:
        return None
    pattern = r"^\d+\."
    queries_list = pre_cot_str.split("\n")
    queries_list = [re.sub(pattern, "", s) for s in queries_list]
    queries_list = [s.lstrip().rstrip() for s in queries_list]
    queries_list = [query for query in queries_list if query != ""]
    return queries_list

def get_hash_id(item, oss_id):
    """要求输入的item为dict形式，含有poly、page、oss_id三个key"""
    hash_id = hashlib.md5((str(item.get('poly'))+str(item.get('page'))+str(oss_id)).encode('utf-8')).hexdigest()
    return hash_id

def insert_mongodb(cot_oss_id, data_to_insert):
    try:
        PdfOutlineResult.objects(oss_id=cot_oss_id).delete()
        docs = [PdfOutlineResult(**item) for item in data_to_insert]
        PdfOutlineResult.objects.insert(docs)
    except Exception as e:
        print(f"mongo insert error: {e}, 准备存到mongodb的数据：{data_to_insert}")
      

def extract_mongo_data(oss_id):
    pa_c = PdfOutlineResult.objects(oss_id=oss_id).all()
    if pa_c == None:
        return []
    return pa_c
    

if __name__ == "__main__":
    # 本地测试, 解注释这里--- 
    from mongoengine import connect
    mongo_config = {
        "Host": "xxx",
        "Port": 27018,
        "DB": "llm",
        "Username": "admin",
        "Password": "admin123",
        "authDB": "admin"
    }
    # 构建连接字符串
    connection_string = (
        f"mongodb://{mongo_config['Username']}:{mongo_config['Password']}@"
        f"{mongo_config['Host']}:{mongo_config['Port']}/"
        f"{mongo_config['DB']}?authSource={mongo_config['authDB']}"
    )
    connect(host=connection_string)
    ####---

    from include.utils.text_utils import get_md5
    query = "请帮我做一个中国近7年石油消耗的走势"
    # query = "请对文档分析并概括总结主要内容"
    context = DocQAContext(session_id=get_md5(query))
    oss_id = "oss://public-xinyu/test-env/doc_search/test1/test_finance_0913.pdf"
    context.add_single_question(request_id=get_md5(query), question_id=get_md5(query), question=query, pdf_ids = oss_id)
    context.set_doc_query_type("具体问题")
    # ####test1
    with open("/Users/xxx/Downloads/sample_outline_cn.json", "r") as f:
        document = json.load(f)
    PdfOutlineResult.objects(oss_id=oss_id).delete()  # 清空
    document = {"data":[{
            "type": "title",
            "uid": "eb29b2351e-4d14-469a-84ae-4b16211970e82",
            "page": 1,
            "poly": [0.12, 0.13, 0.14, 0.15],
            "text": "我国历年来石油储备量勘探记录对提振工业经济发展的贡献"
        },{
            "type": "title",
            "uid": "eb29b2351e-4d14-469a-84ae-4b16211970e82",
            "page": 112,
            "poly": [0.12, 0.13, 0.14, 0.15],
            "text": "过去十年全球石油消耗形势图"
        },{
            "type": "title",
            "uid": "eb29b2351e-4d14-469a-84ae-4b16122340e82",
            "page": 2,
            "poly": [0.12, 0.13, 0.14, 0.15],
            "text": "目录"
        },{
            "type": "table_caption",
            "uid": "ebsb2351e-4d14-469a-84ae-4b16211970e82",
            "page": 192,
            "poly": [0.12, 0.13, 0.14, 0.15],
            "text": "2022年以来中国第二产业发展曲线图"
        },{
            "type": "table_caption",
            "uid": "eb29b2351e-4fdd14-469a-84ae-4sd0e82",
            "page": 2234,
            "poly": [0.22, 0.13, 0.14, 0.15],
            "text": "请帮我做一个中国近7年石油消耗的走势图"
        }]}
    import uuid
    for i in range(100):
        document["data"].append({
            "type": "title",
            "uid": str(uuid.uuid4()),
            "page": str(i),
            "poly": [0.12, 0.13, 0.23, 0.15],
            "text": "菲律宾用电量统计图" + str(i)
        })
    res = DocPreCOT().pre_doc_cot("docid", oss_id, document)
    print("mongoDB储蓄：", res)
    exit()

    # test1
    res = extract_mongo_data("oss://public-xinyu/test-env/doc_search/test1/17a45f709b5a9a1773e941f199bc5d19.pdf")
    print(res)


    # # ####test2
    cot_tool = QueryDivisionDocCoTTask(context)
    cot_tool.get_cot()
    res = context.get_dag().get_turns()