import traceback

from pymilvus import Milvus, MilvusClient, DataType, FieldSchema, CollectionSchema
from include.config import CommonConfig
import json
import requests

uri = CommonConfig['MILVUS']['uri']
user = CommonConfig['MILVUS']['username']
passwd = CommonConfig['MILVUS']['password']
client = MilvusClient(uri=uri, user=user, password=passwd)


chunk_split_model = CommonConfig['CHUNK_SPLIT']['model']
url = CommonConfig['FSCHAT']['general_url']
token = CommonConfig['AUTH_CONFIG']['key']

def create_collection():
    ainews_pdf_qa_schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    ainews_pdf_qa_schema.add_field(field_name="uid", datatype=DataType.VARCHAR, is_primary=True, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="oss_id", datatype=DataType.VARCHAR, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="user_id", datatype=DataType.VARCHAR, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="origin_content", datatype=DataType.VARCHAR, max_length=20480)
    ainews_pdf_qa_schema.add_field(field_name="page_num", datatype=DataType.VARCHAR, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="chunk", datatype=DataType.VARCHAR, max_length=20480)
    ainews_pdf_qa_schema.add_field(field_name="chunk_num", datatype=DataType.VARCHAR, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="chunk_poly", datatype=DataType.VARCHAR, max_length=1024)
    ainews_pdf_qa_schema.add_field(field_name="reserve_expansion", datatype=DataType.VARCHAR, max_length=10240)
    ainews_pdf_qa_schema.add_field(field_name="bge_base_zh_embedding_general", datatype=DataType.FLOAT_VECTOR, dim=768)

    client.create_collection(collection_name = "ainews_pdf_qa_collection", schema=ainews_pdf_qa_schema)

# 升级milvus client，该用up_insert插入，默认id主键
def save_to_milvus(collection_name , embedding_data):
    rows = list()
    for item in embedding_data:
        row = {"uid": item["uid"], "doc_id": item["doc_id"], "oss_id": item["oss_id"], "user_id": item["user_id"], 
               "origin_content": item["origin_content"], "page_num": item["page_num"], "chunk": item["chunk"], 
               "chunk_num": item["chunk_num"], "chunk_poly": item["chunk_poly"], "reserve_expansion": item["mode"], 
               "bge_base_zh_embedding_general": item["bge_base_zh_embedding_general"]}
        rows.append(row)
    # mr = client.insert(collection_name, rows)
    mr = client.upsert(collection_name, rows)
    return mr

def delete_from_milvus(collection_name, doc_id, user_id, mode):
    # 插入前先按照doc_id删除数据
    mdr = client.delete(collection_name=collection_name, filter=f'doc_id == "{doc_id}" and user_id  == "{user_id}" and reserve_expansion == "{mode}"')
    return mdr

def query_embedding(request_id, queries):
    payload = json.dumps({
                "model": chunk_split_model,
                "params": {
                    "request_id": request_id,
                    "batch_seq": queries,
                    "text_splitter_config": {
                        "splitter_type": "Recursive",
                        "only_splitter": False,
                        "Recursive": {
                            "chunk_size": 350,
                            "chunk_overlap": int(75),
                            "chunk_max_size": 2000
                        },
                    }
                }
            })
    headers = {
        'token': token,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    texts = json.loads(response.text)

    data = list()
    for text in texts:
        data.append(text[2])
    return data

def load_from_milvus(queries, doc_id = [], user_id = 'test1', mode = True, similarity_threshold = 0, topk = 10, model:str = 'bge_base_zh_embedding_general'):
    results = list()
    mode = 'textonly' if mode else 'fast'
    collection_name = 'ainews_pdf_qa_collection'
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 30}}
    try:
        mlv_results = client.search(
            collection_name=collection_name,  
            data=queries, 
            anns_field = model, 
            search_params=search_params,
            limit=topk, 
            filter=f"oss_id in {doc_id} and user_id == '{user_id}' and reserve_expansion == '{mode}'",
            output_fields=['doc_id', 'oss_id', 'user_id', 'origin_content', 'page_num', 'chunk', 'chunk_num', 'chunk_poly'],
            timeout=1
        )
    except Exception as e:
        traceback.print_exc()
        return results
    
    mlv_results = json.loads(json.dumps(mlv_results))
    for result in mlv_results[0]:
        # if result["distance"] > similarity_threshold:
            result_dict = dict()
            result_dict['score'] = result["distance"]
            result_dict['doc_id'] = result["entity"].get('doc_id')
            result_dict['oss_id'] = result["entity"].get('oss_id')
            result_dict['user_id'] = result["entity"].get('user_id')
            result_dict['chunk'] = result["entity"].get('chunk')
            result_dict['chunk_num'] = result["entity"].get('chunk_num')
            result_dict['origin_content'] = result["entity"].get('origin_content')
            result_dict['chunk_poly'] = result["entity"].get('chunk_poly')
            result_dict['page_num'] = result["entity"].get('page_num')
            results.append(result_dict)
    return results

if __name__ == '__main__':
    # create_collection()
    queries = ["假设你是著名的首席宏观经济分析师，请你仔细阅读这篇宏观研究报告，并写一篇1000字左右的总结。"]
    queries_embedding = query_embedding('test123',queries)
    print(len(queries_embedding))
    # print(queries_embedding)
    
    res = load_from_milvus(queries_embedding, doc_id=["oss://public-xinyu/test-env/doc_search/test1/09f668cc9f19475b3ade79bda7411228.pdf"], user_id='test_1234', mode = True)
    print(len(res))
    print(res)

    # mdr = client.delete(collection_name='ainews_pdf_qa_collection', filter='doc_id == "09f668cc9f19475b3ade79bda7411228"')
    # print(mdr)
