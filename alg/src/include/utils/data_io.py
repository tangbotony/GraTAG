from elasticsearch import Elasticsearch
from include.config import CommonConfig


es_user = Elasticsearch(hosts=CommonConfig['ES_USER']['url'], http_auth=('elastic', CommonConfig['ES_USER']['elastic']))


def es_qa_search_by_material_ids(material_ids):
    body = {
        "query": {
            "terms": {
                "material_id": material_ids
            }
        }
    }
    res = es_user.search(index="xinhuatest", body=body)
    ret = {}
    for item in res['hits']['hits']:
        ret[item['_source']['material_id']] = item['_source']['context']
    return ret


def get_doc_from_es(material_id: list):
    materials = es_qa_search_by_material_ids(material_id)
    doc = list(materials.values())
    return doc, materials


def return_md5_id_with_text(text):
    from hashlib import md5
    obj = md5()
    obj.update(text.encode("utf-8"))
    return obj.hexdigest()


def get_material_group_id(material_id_list: list) -> str:
    material_id_list.sort()
    # 根据材料id构造session_id
    return return_md5_id_with_text("".join(material_id_list))


def get_docs(context):
    material_id = context.get_material_id()
    load_from_es = context.is_load_from_es()
    if int(context.get_type()) > 0:
        structure_context = context.get_structure_context()
        doc_info_dic = dict()
        for part in [structure_context['pre'], structure_context['ending']] + structure_context['other']:
            if len(part.get('ori_content', '')) > 0 or len(part.get('content', '')) > 0:
                content = part.get('content', '') if part.get('content', '') != "" else part.get('ori_content', '')
                if part['material_id'] not in doc_info_dic:
                    doc_info_dic[part['material_id']] = content + '\n'
                else:
                    doc_info_dic[part['material_id']] += content + '\n'
        docs = list(doc_info_dic.values())
    else:
        if load_from_es:
            docs, doc_info_dic = get_doc_from_es(material_id)
        else:
            documents = context.get_document()
            docs = list(documents.values())
            doc_info_dic = documents
    return docs, doc_info_dic
