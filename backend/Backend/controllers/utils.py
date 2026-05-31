from webargs.flaskparser import parser
from webargs.multidictproxy import MultiDictProxy
import json
import requests
from config import config_manager
from controllers import ALLOWED_IMAGE, ROOT_ID, ROOT_NAME
from models.document import Document, FileMeta
from iaar_retriever import query_iaar_summary

algorithm_url = config_manager.default_config['ALGORITHM_2_URL']

def change_to_meta(list_file):
    res = []
    for item in list_file:
        res.append(FileMeta(item))
    return res

def get_path(parent_id, id, name, user_id):
    path = [(ROOT_ID, ROOT_NAME)]
    if parent_id == ROOT_ID:
        path.append((id, name))
        return path
    
    parent_doc = Document.objects(_id=parent_id, user_id=user_id, is_trash=False, is_delete=False).first()
    path = parent_doc.path
    path.append((id, name))
    return path

def validator_id():
    pass

def validator_parent_id(parent_id, user_id):
    if parent_id == ROOT_ID:
        return True
    doc = Document.objects(_id=parent_id, user_id=user_id, is_trash=False, is_delete=False).first()
    return doc is not None

@parser.location_loader("form_and_files")
def load_data(request, schema):
    newdata = request.form.copy()
    newdata.update(request.files)
    return MultiDictProxy(newdata, schema)

def validate_image(filename):
    for item in ALLOWED_IMAGE:
        if filename.endswith(item):
            return True
    return False


search_baidu_service = config_manager.baidu_config['url']
headers = {"token":config_manager.default_config['SIMILARITY_TOKEN'],
                        'Content-Type': 'application/json',}

def query_baidu(raw_text, max_entries=10, mode="default", get_content=0, query='summary', search_type='news',
                block=None, timeout=10):
    """
    :param max_entries:
    :param raw_text: 待查询文本
    :param mode:
    :param get_content: 是否拿全文内容
    :param query: summary / keyword
    :param search_type: news/page
    :param block
    :return: 结果dict
    """
    try_num = 3
    baidu_query = raw_text.strip()[:100]
    # if len(raw_text) < 100:
    #     baidu_query = raw_text.strip()
    # elif query == "summary":
    #     baidu_query = get_query_abstract(raw_text)
    # else:
    #     baidu_query = ' '.join(self.get_search_keywords(raw_text))
    # baidu_query = baidu_query + ' -site:' + block if block else baidu_query
    payload = json.dumps({"keyword": baidu_query, "mode": mode, "search_type": search_type,
                            "max_entries": max_entries, "get_content": get_content})
    res, err = None, None
    while try_num:
        try:
            try_num -= 1
            res_temp = requests.request("POST", search_baidu_service, headers=headers,
                                    data=payload, timeout=timeout)    
            res = eval(res_temp.content)
            if res == {"msg": "No valid URL found!"}:
                err = f"{baidu_query} No valid URL found!"
                continue
            
            return res, None
                # logger.warning(f"{baidu_query} No valid URL found!")
                # res = []

        except SyntaxError as e:
            err = str(e)
            # logger.warning(f"{baidu_query} error {res_temp.text}")
            # res = []
        
    return res, err


def query_network(raw_text, max_entries=10, mode="default", get_content=1, query='summary', search_type='news',
                block=None, timeout=10):
    """
    :param max_entries:
    :param raw_text: 待查询文本
    :param mode:
    :param get_content: 是否拿全文内容
    :param query: summary / keyword
    :param search_type: news/page
    :param block
    :return: 结果dict
    """
    baidu_query = raw_text.strip()[:100]

    body = {
            "request_id": "10088",
            "queries": baidu_query,
            "return_num": max_entries,
            "baidu_field": {"switch": False, "type": "page"},
            "bing_field": {"switch": True, "type": "page"},
            "sogou_field": {"switch": False, "type": "page"}
            }

    res, err = None, None
    ret = None
    try:
        headers = {
          "token":"20548cb5a329260ead027437cb22590e945504abd419e2e44ba312feda2ff29e"
        }
        dynamic_headers = headers.copy()
        dynamic_headers['language'] = "zh-CN"
        url = algorithm_url + "/ref_event_recommend"
        res_t = requests.post(url, headers=dynamic_headers, json=body)
        # res_t, type, flag = query_iaar_summary(body, token= "ecd71870d1963316a97e3ac3408c9835ad8cf0f3c1bc703527c30265534f75ae")
        res = []
        ret = res_t.json()['result']
        for r in ret:
            r2 = {}
            r2['content'] = r['summary']
            r2['description'] = r['summary']
            r2['title'] = r['title']
            r2['url'] = r['url']
            res.append(r2)

    except Exception as e:
        error = f"{baidu_query} baidu_error {e}"
        err = f"baidu_error: {error}"

    return res, err

if __name__ == "__main__":
    res, err = query_network("巴黎奥运会", max_entries=10)
    print(res)