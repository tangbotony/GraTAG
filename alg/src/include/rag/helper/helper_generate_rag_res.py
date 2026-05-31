
def generate_rag_res(check_items: dict):
    """
    [
    {
        "description": "xxxx",  # 相关内容
        "id": "xxxx",  # 内容id
        "title": "XXXX",  # 标题
        "source": "1",  # 数据库来源标识
        "source_id": ""  # 稿件id 引证内容的主键（doc_id）
        "type_id": ""  # 引证内容的主键（type_id）
    },
    {
        "description": "xxxx",
        "id": "xxxx",
        "title": "XXXX",
        "source": "1",  # 数据库来源标识
        "source_id": ""  # 引证内容的主键（doc_id）
        "type_id": ""  # 引证内容的主键（type_id）
    },
    .......
    ]
    """
    rag_res = []
    for key, item in check_items.items():
        rag_res.append({
            "description": item['description'],
            "id": item['id'],
            "title": item['title'],
            "theme": item["theme"],
            "source": item['source'],
            "source_id": item['source_id'],
            "type_id": "",
            "other_info": item['other_info'],
            "key":key
        })
    return rag_res