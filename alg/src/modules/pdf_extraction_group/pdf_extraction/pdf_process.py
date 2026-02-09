import requests
from json.decoder import JSONDecodeError
from include.utils.milvus_utils import save_to_milvus, delete_from_milvus
from include.utils.similarity_utils import get_chunk_embeddings
from include.utils.mongo_utils import PdfExtractResult
from include.utils.text_utils import process_text, find_original_content
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from include.logger import ContextLogger
from include.config import CommonConfig
from include.decorator import timer_decorator
from modules.query_division_based_cot_group.query_division_doc_cot_group import DocPreCOT

MOLTIMODAL_URL = CommonConfig['PDF_PROCESS_CONFIGS']['multimodal_url']
MOLTIMODAL_DISABLE = CommonConfig['PDF_PROCESS_CONFIGS']['multimodal_disable']
PDF_EXTRACT_URL = CommonConfig['PDF_PROCESS_CONFIGS']['pdf_extract_url']
CHUNK_MODEL = CommonConfig['CHUNK_SPLIT']['model']
CHUNK_URL = CommonConfig['FSCHAT']['general_url']

logger = ContextLogger()

headers = {
    'token': 'xxx',
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}


def merge_pdf_elements(elements, max_text_length=2000, max_num_poly=5):
    """
    我有一个list of dict，代表对一个pdf解析出来的模块信息，举个例子：
    [
        {'page': 1, 'text': '证券研究报告', 'type': 'plain text'},
        {'page': 1, 'text': '一、经济研究', 'type': 'title'},
        {'page': 1, 'text': 'xxxxxxxxxxxxx', 'type': 'plain text'},
        {'page': 1, 'text': 'xxxxxxxxxxxxx', 'type': 'plain text'},
        {'page': 1, 'text': 'this is a table', 'type': 'table'},
        {'page': 1, 'text': 'xxxxxxxxxxxxx', 'type': 'plain text'},
        {'page': 1, 'text': 'xxxxxxxxxxxxx', 'type': 'title'},
        {'page': 2, 'text': 'xxxxxxxxxxxxx', 'type': 'title'},
    ]
    格式大概就是这样，我希望将其中的元素进行合并。合并规则如下：
    1. 仅合并相邻的元素（可以跨页）
    2. title尽量和其后的plain text合并在一起，如果遇到连续的title也可以进行合并
    3. 每个合并后的元素，text是所有参与合并的text的元素之和，page是所有参与合并的page的列表，如[1, 1, 2], type是所有参与合并的type的列表，如['title', 'title', 'plain text']，
    4. 合并后的总的text不得超过2000字, 合并的元素个数不超过5个
    """
    merged_elements = []
    current_element = None

    def append_element():
        """Helper to append current_element to merged_elements and reset."""
        if current_element:
            merged_elements.append(current_element.copy())

    for elem in elements:
        # If it's the first element or the type is 'table'/'fig', create a new entry
        if current_element is None:
            current_element = {
                'page': [elem['page']],
                'poly': [elem['poly']],
                'text': [elem['text']],
                'type': [elem['type']],
                'uid': [elem['uid']],
                'origin_text': [elem['input_text']],
                'input_text': elem['input_text']
            }
        elif elem['type'] in ['title', 'plain text', 'table', 'fig_caption', 'figure_caption', 'table_caption']:
            # Try to merge titles and plain text
            combined_text = current_element['input_text'] + '\n' + elem['input_text']
            if len(combined_text) <= max_text_length and len(current_element['poly']) <= max_num_poly:
                current_element['page'].append(elem['page'])
                current_element['poly'].append(elem['poly'])
                current_element['text'].append(elem['text'])
                current_element['type'].append(elem['type'])
                current_element['uid'].append(elem['uid'])
                current_element['origin_text'].append(elem['input_text'])
                current_element['input_text'] = combined_text
            else:
                append_element()
                current_element = {
                    'page': [elem['page']],
                    'poly': [elem['poly']],
                    'text': [elem['text']],
                    'type': [elem['type']],
                    'uid': [elem['uid']],
                    'origin_text': [elem['input_text']],
                    'input_text': elem['input_text']
                }
        else:
            print("elem['type'] in ['title', 'plain_text', 'table']")

    # Append the last element if not yet appended
    append_element()
    return merged_elements


def multimodal_image_process(pdf_element):
    image_url = pdf_element.get('url')
    payload = json.dumps({
        "image_oss_id": [
            f"https://public-pdf-extract-kit.oss-cn-shanghai.aliyuncs.com/{image_url}"
        ]
    })
    response = requests.request("POST", MOLTIMODAL_URL, headers=headers, data=payload, timeout=40)
    res = json.loads(response.text)
    pdf_element['text'] = res.get('image_text','')
    return pdf_element

"""
embedding预处理,用于获取需要embedding的文本信息
mode: fast/normal/accurate
fast模式: 直接获取pdf_element的text字段,返回类型为str
other模式(normal/accurate): 提取块中poly信息,返回类型为list
"""
from typing import Union
def pre_embedding_process(pdf_results, mode, type_) -> Union[list, str]:
    if type_ == 'txt':
        return ''.join(result.get('text', '') for result in pdf_results)
    if mode == 'fast':
        return [result.get('data', {}) for result in pdf_results]
    return [item for item in pdf_results if item.get('text')]

"""
embedding调用,存储milvus向量库
raw_text: [{text:xxx, num:xxx, poly:xxx, page:xxx}]
"""
def chunk_embedding_process(raw_text, oss_id, user_id, mode, chunk_size=500, overlap=350 * 0.25, chunk_max_size=2000):
    doc_id = str(oss_id).split('/')[-1].split('.')[0]
    base_index = 0
    # 开发完成后使用upsert方式，不进行删除操作
    mdr = delete_from_milvus('ainews_pdf_qa_collection', doc_id, user_id, mode)
    logger.info(f'pdf extraction delete from milvus success, res: {mdr}')
    if isinstance(raw_text, str):
        for i in range(0, len(raw_text), 50000):  # TODO: 分割符分割
            input_text = [process_text(raw_text[i:i + 50000])]
            result = list()
            texts = get_chunk_embeddings(input_text, oss_id)
            # 调用函数
            texts = find_original_content(raw_text[i:i + 50000], input_text[0], texts)

            for index, text in enumerate(texts):
                embedding_result = dict()
                try:
                    chunk = json.loads(text[1]).get('chunk','')
                    embedding_result['uid'] = hashlib.md5((doc_id+user_id+chunk).encode('utf-8')).hexdigest()
                    embedding_result['doc_id'] = doc_id
                    embedding_result['oss_id'] = oss_id
                    embedding_result['user_id'] = user_id
                    embedding_result['mode'] = mode
                    embedding_result['chunk'] = chunk
                    embedding_result['chunk_num'] = str(index + base_index)
                    embedding_result['origin_content'] = str([text[3].get('origin_content', chunk)])
                    embedding_result['page_num'] = '[]'
                    embedding_result['chunk_poly'] = '[]'
                    embedding_result['bge_base_zh_embedding_general'] = text[2]
                    result.append(embedding_result)
                except Exception as e:
                    logger.info(str(e))
            base_index += len(texts)
            logger.info(f'embedding success, length: {len(result)}')
            milvus_res = save_to_milvus('ainews_pdf_qa_collection', result)
            logger.info('pdf extraction insert into milvus success')
            logger.info(milvus_res)
    elif isinstance(raw_text, list):
        for item in raw_text:
            item.update({"input_text": process_text(item.get('text'))})
        merged_raw_text = merge_pdf_elements(raw_text)
        input_text = [item.get('input_text') for item in merged_raw_text]

        result = list()
        texts = get_chunk_embeddings(input_text, oss_id, chunk_size=5000, overlap=0, chunk_max_size=5000)
        for text in texts:
            embedding_result = dict()
            try:
                chunk = json.loads(text[1]).get('chunk','')
                page_num = merged_raw_text[text[0]].get('page')
                chunk_poly = merged_raw_text[text[0]].get('poly')
                origin_input_text = merged_raw_text[text[0]].get('origin_text')
                embedding_result['uid'] = hashlib.md5((oss_id+user_id+str(page_num)+str(chunk_poly)).encode('utf-8')).hexdigest()
                embedding_result['doc_id'] = doc_id
                embedding_result['oss_id'] = oss_id
                embedding_result['user_id'] = user_id
                embedding_result['mode'] = mode
                embedding_result['chunk'] = chunk
                embedding_result['chunk_num'] = str(text[0])
                embedding_result['origin_content'] = str(origin_input_text)
                embedding_result['page_num'] = str(page_num)
                embedding_result['chunk_poly'] = str(chunk_poly)
                embedding_result['bge_base_zh_embedding_general'] = text[2]
                result.append(embedding_result)
            except Exception as e:
                logger.info(str(e))
        logger.info(f'embedding success, length: {len(result)}')
        milvus_res = save_to_milvus('ainews_pdf_qa_collection', result)
        # milvus_res = save_to_milvus('ainews_doc_qa_collection', result)
        logger.info(f'pdf extraction insert into milvus success, milvus res: {milvus_res}')
    else:
        logger.warning(f'input raw_text type is illegal')


"""
存储中间结果到mongodb
"""
def save_pdf_extract_result_tomongo(pdf_results, oss_id):
    try:
        PdfExtractResult.objects(oss_id=oss_id).delete()
        mongo_save = [{**item, "oss_id": oss_id, "_id":hashlib.md5((str(item.get('poly'))+str(item.get('page'))+oss_id).encode('utf-8')).hexdigest()} for item in pdf_results]
        docs = [PdfExtractResult(**item) for item in mongo_save]
        PdfExtractResult.objects.insert(docs)
    except Exception as e:
        logger.error(f"mongo insert error: {e}")


@timer_decorator
def pdf_process(_id, oss_id, user_id, mode, type_, context=None):
    # pdf文件解析处理
    file_id = hashlib.md5(oss_id.encode('utf-8')).hexdigest()
    st = time.time()
    pdf_results = process_pdf(_id, oss_id, file_id, mode, type_)
    if not pdf_results:
        logger.error(f'pdf extraction service timeout, and time cost: {time.time()-st}')
        return 'failed'
    logger.info(f'pdf extraction process success, and time cost: {time.time()-st}')
    
    # 中间结果存储到mongo
    if mode in ['textonly']:
        save_pdf_extract_result_tomongo(pdf_results, oss_id)
        logger.info(f'pdf extraction result: {len(pdf_results)}, insert into mongo success')

    # 预处理
    pre_embedding = pre_embedding_process(pdf_results, mode, type_)
    logger.info(f'pre embedding process success, length: {len(pre_embedding)}')

    # embedding and save to milvus
    chunk_embedding_process(pre_embedding, oss_id, user_id, mode)
    return 'success'


def process_pdf(_id: str, oss_id: str, file_id: str, mode: str, type_: str) -> list:
    if type_ == 'txt' or mode == 'fast':
        return process_fast_mode(oss_id, file_id,)
    else:
        if mode == 'textonly':
            return process_textonly_mode(_id, oss_id, file_id)
        else:
            return process_extract_mode(oss_id, file_id)


@timer_decorator
def process_fast_mode(oss_id: str, file_id: str):
    outline_executor = ThreadPoolExecutor(max_workers=2)

    files = {
        'oss_id': (None, oss_id),
        'process_type': (None, 'fast'),
        'file_id': (None, file_id),
        'is_stream': (None, False)
    }

    # 切换muxi pdf解析接口
    # todo: 是否还需切换回电信pdf解析服务
    header = {
        'Authorization': 'xxx'
    }
    response = requests.post(PDF_EXTRACT_URL, headers = header, files=files, timeout=40)

    if response.status_code!= 200:
        logger.error(f"pdf extract error: {response.text}")
        return []
    resp = json.loads(response.text)
    pdf_element_res = resp.get('file_result',[])

    # 大纲处理逻辑
    pdf_outline_res = resp.get('outline',[])
    if pdf_outline_res:
        pass
    return pdf_element_res


@timer_decorator
def process_textonly_mode(_id:str, oss_id: str, file_id: str):
    outline_executor = ThreadPoolExecutor(max_workers=2)

    files = {
        'oss_id': (None, oss_id),
        'process_type': (None, 'text-only'),
        'file_id': (None, file_id),
        'is_stream': (None, False)
    }

    max_retries = 2
    retries = 0

    while retries < max_retries:
        try:
            header = {
                'Authorization': 'xxx'
            }
            response = requests.post(PDF_EXTRACT_URL, headers=header, files=files, timeout=40)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            retries += 1
            if retries >= max_retries:
                logger.error(f"pdf extract error after {max_retries} attempts: {e}")
                return []
            logger.warning(f"pdf extract attempt {retries} failed: {e}. Retrying...")

    resp = json.loads(response.text)
    pdf_element_res = resp.get('file_result',[])

    # 大纲处理逻辑
    pdf_outline_res = resp.get('outline',[])
    docprecot = DocPreCOT()
    if pdf_outline_res:
        outline_executor.submit(docprecot.pre_doc_cot, _id, oss_id, pdf_outline_res)
    return pdf_element_res


@timer_decorator
def process_extract_mode(oss_id: str, file_id: str):
    pdf_results = list()
    futures = list()
    files = {
        'oss_id': (None, oss_id),
        'process_type': (None, 'default'),
        'file_id': (None, file_id)
    }

    response = requests.post(PDF_EXTRACT_URL, files=files, stream=True, timeout=40)
    outline_executor = ThreadPoolExecutor(max_workers=5)
    multimodal_executor = ThreadPoolExecutor(max_workers=20)
    
    for chunk in response.iter_lines(chunk_size=1024,decode_unicode=False,delimiter=b"\n\n"):
        if chunk:
            content = chunk.decode('utf-8')
            if content.startswith("data: ") and content != "data: [DONE]\n\n":
                content = content[len("data: "):]
                try:
                    content = json.loads(content)
                except JSONDecodeError as e:
                    logger.info(f"JSONDecodeError: {e}")
                    continue

                if content['type']=="element":
                    pdf_element = content['data']
                    ele_type = pdf_element['type']
                    
                    if ele_type in ["text", "plain text", "table_caption", "figure_caption"]:
                        pdf_results.append(pdf_element)
                    elif ele_type in ["table", "figure"]:
                        url = pdf_element.get('url','')
                        if not MOLTIMODAL_DISABLE and url.startswith("pdf-extracted-element"):
                            future = multimodal_executor.submit(multimodal_image_process, pdf_element)
                            futures.append(future)
                    else:
                        pass

                # 触发大纲逻辑
                elif content['type']=="outline":
                    pdf_outline = content['data']
                    if pdf_outline:
                        # outline_executor.submit()
                        pass

                else:
                    pass

    image_results = list()
    for future in as_completed(futures):
        try:
            result = future.result()
            image_results.append(result)
        except Exception as e:
            logger.info(e)
    
    pdf_results.extend(image_results)
    logger.info(f'pdf extraction process success, length: {len(pdf_results)}')
    return pdf_results


import hashlib
import time
if __name__ == '__main__':
    # file upload and process
    st = time.time()
    oss_id = 'oss://public-pdf-extract-kit/test-env/doc_xxx/samples_inner.txt'
    file_id = hashlib.md5(oss_id.encode('utf-8')).hexdigest()
    logger.info(file_id)
    pdf_process('test_123', oss_id, 'test123', mode='fast', type_='pdf')
    logger.info(time.time()-st)

    # milvus_test
    from include.utils.milvus_utils import load_from_milvus, query_embedding

    queries = ["报告中宏观经济指的是什么"]
    queries_embedding = query_embedding('test123', queries)
    res = load_from_milvus(queries_embedding,
                           doc_id=[oss_id], topk=100, user_id='test123')
    print(res)
    res = load_from_milvus(queries_embedding,
                           doc_id=[oss_id], topk=100)
    print(res)
    res = load_from_milvus(queries_embedding,
                           doc_id=[oss_id], topk=100)
    print(res)
    res = load_from_milvus(queries_embedding,
                           doc_id=['pdf-source-file/example.pdf'], topk=100)
    print(res)
