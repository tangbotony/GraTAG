import threading
from config import config_manager, logging
from elasticsearch import Elasticsearch



_lock_es_material = threading.Lock()
ES_INDEX_NAME_MATERIAL= "material_v1"
ES_INDEX_MATERIAL_CREATED = False


es_client = Elasticsearch(hosts=config_manager.es_config['url'], http_auth=(config_manager.es_config['auth'], config_manager.es_config['passwd']))


def create_es_index_materal():
    global ES_INDEX_MATERIAL_CREATED, _lock_es_material
    if ES_INDEX_MATERIAL_CREATED:
        return True
    
    with _lock_es_material:
        mapping_material = {

            "mappings": {
                "properties": {     
                    "material_id":{
                        "type": "keyword",
                    },
                    'content': {'properties': {'context': {'type': 'text', 'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}}}}}, 
                    'context': {'type': 'text', 'analyzer': 'ik_max_word'}, 
                    'doc_id': {'type': 'keyword'},
                    'group_id': {'type': 'integer'}, 
                    "material_name": {'type': 'text', 'analyzer': 'ik_max_word'}, 
                    "src_type": {
                        "type": "integer",
                    },
                    "ext": {
                        "type": "keyword",
                    },
                    "user_id": {
                        "type": "keyword",
                    },            
                    "raw_file_path": {
                        "type": "keyword",
                    },
                    "insert_time": {
                        "type": "date",
                    },
                    "update_time": {
                        "type": "date",
                    }, 
                    "status": {
                        "type": "integer",  # 0 just insert, 1 used
                    },                    
                }

            }
        }

        if es_client.indices.exists(index=ES_INDEX_NAME_MATERIAL):
            logging.logger.info(f"索引 {ES_INDEX_NAME_MATERIAL} 已创建")
        else:
            # 创建索引
            es_client.indices.create(index=ES_INDEX_NAME_MATERIAL, body=mapping_material)
            if es_client.indices.exists(index=ES_INDEX_NAME_MATERIAL):
                logging.logger.info(f"索引 {ES_INDEX_NAME_MATERIAL} 创建成功")
            else:
                logging.logger.info(f"索引 {ES_INDEX_NAME_MATERIAL} 创建失败")
                return False
            
        
        ES_INDEX_MATERIAL_CREATED = True
        return True

def save_material_to_es(id,doc):
    if not create_es_index_materal():
        raise Exception("es not ready")
    
    res = es_client.index(index=ES_INDEX_NAME_MATERIAL,id=id,body=doc,refresh="wait_for")
    return res

def search_context_by_material_ids_from_es(material_ids):
    body = {
        "_source":["material_id","context"],
        "query": {
            "terms": {
                "material_id": material_ids
            },

        }
    }    
    return search_from_es(body,only_filed="context")

def search_file_info_by_material_ids_from_es(material_ids):
    body = {
        "_source":["material_id","material_name","ext","raw_file_path"],
        "query": {
            "terms": {
                "material_id": material_ids
            },
        }
    }    
    return search_from_es(body)

def search_all_by_material_ids_from_es(material_ids):
    body = {
        "query": {
            "terms": {
                "material_id": material_ids
            }
        }
    }    
    return search_from_es(body)


def get_file_info_by_id_from_es(id):
    try:
        res = es_client.get(index=ES_INDEX_NAME_MATERIAL, id=id,_source=["material_id","material_name","ext","raw_file_path"])
        if res['found']: 
            return res['_source']
        else:
            return None
    except Exception as e:
        return None

# def get_raw_file_path_by_id_from_es(id):
#     res = es_client.get(index=ES_INDEX_NAME_MATERIAL, id=id,_source=["raw_file_path"])
#     if res['found']: 
#         return res['_source']['raw_file_path']
#     else:
#         return None

def search_from_es(body, only_filed=None):    
    res = es_client.search(index=ES_INDEX_NAME_MATERIAL, body=body)
    ret = {}
    for item in res['hits']['hits']:        
        k = item['_id']
        if only_filed:
            ret[k] = item['_source'][only_filed]
        else:
            ret[k] = item['_source']
    return ret

