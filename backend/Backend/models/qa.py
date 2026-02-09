import mongoengine as me

# 问题补全
class Additional_query(me.EmbeddedDocument):
    options = me.ListField(me.StringField(), default=[])
    selected_option = me.ListField(me.StringField(), default=[])
    other_option = me.StringField(default="")#用户手动输入
    title = me.StringField()

# 参考文档
class Ref_page(me.EmbeddedDocument):
    _id = me.StringField(required=True, primary_key=True)
    url = me.StringField()
    site = me.StringField()
    title = me.StringField()
    summary = me.StringField()
    content = me.StringField()
    icon = me.StringField()

# 问答对说明
class Qa_pair_info(me.EmbeddedDocument):
    site_num = me.IntField()
    page_num = me.IntField()
    word_num = me.IntField()
    additional_query =  me.EmbeddedDocumentField(Additional_query)
    search_query = me.ListField(me.StringField(), default=[])
    ref_pages = me.MapField(me.EmbeddedDocumentField(Ref_page), default={})

# 问答引证
class Answer_ref(me.EmbeddedDocument):
    _id = me.StringField(required=True, primary_key=True)
    news_id = me.StringField()
    content = me.StringField()

# 单个问答对 ✅
class Qa_pair(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    version = me.IntField()
    qa_pair_collection_id = me.StringField(required=True)
    qa_series_id = me.StringField(required=True)
    query = me.StringField()
    qa_info =  me.EmbeddedDocumentField(Qa_pair_info)
    general_answer = me.StringField()
    images = me.ListField(default=[])
    timeline_id = me.StringField()
    recommend_query = me.ListField(me.StringField(), default=[])
    reference = me.ListField(default=[])
    create_time = me.StringField()
    unsupported = me.IntField(default=0)
    search_mode = me.StringField(default="")

class LatestQAPair(me.EmbeddedDocument):
    _id = me.StringField(required=True, primary_key=True)
    version = me.IntField()
    qa_pair_collection_id = me.StringField(required=True)
    qa_series_id = me.StringField(required=True)
    query = me.StringField()
    qa_info = me.EmbeddedDocumentField(Qa_pair_info)
    general_answer = me.StringField()
    images = me.ListField(default=[])
    timeline_id = me.StringField()
    recommend_query = me.ListField(me.StringField(), default=[])
    reference =  me.ListField(default=[])
    create_time = me.StringField()
    unsupported = me.IntField(default=0)
    
# 多个问答对的集合 ✅
class Qa_pair_collection(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    qa_series_id = me.StringField()
    order = me.IntField()
    query = me.StringField()
    qa_pair_list = me.ListField(me.StringField(), default=[])
    is_subscribed = me.BooleanField(default=False)
    subscription_id = me.StringField(default="")
    create_time = me.StringField()
    latest_qa_pair = me.EmbeddedDocumentField(LatestQAPair)


# 单个问答系列 ✅
class Qa_series(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    user_id = me.StringField(required=True)
    title = me.StringField()
    qa_pair_collection_list = me.ListField(me.StringField(), default=[])
    is_search_delete = me.BooleanField(default=False)
    is_qa_delete = me.BooleanField(default=False)
    create_time = me.StringField()

# 时间脉络，字段未定 ✅
class Timeline(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    data = me.DictField(default={})
    create_time = me.StringField()

# 订阅类 ✅
class Subscription(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    qa_series_id = me.StringField(required=True)
    qa_pair_collection_id = me.StringField(required=True)
    query = me.StringField(required=True)
    push_interval = me.IntField(required=True)
    push_time = me.StringField(required=True)
    end_time = me.StringField(required=True)
    email = me.StringField(required=True)
    create_time = me.StringField()
    user_id = me.StringField(required=True)
    fresh_time = me.StringField()
