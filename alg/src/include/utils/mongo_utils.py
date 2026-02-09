import mongoengine as me
from mongoengine import connect
from include.config import CommonConfig
class PdfExtractResult(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    uid = me.StringField()
    oss_id = me.StringField()
    type = me.StringField()
    page = me.StringField()
    poly = me.ListField(me.FloatField())
    text = me.StringField()
    url = me.StringField()

class PdfOutlineResult(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    uid = me.StringField()
    oss_id = me.StringField()
    type = me.StringField()
    page = me.StringField()
    poly = me.ListField(me.FloatField())
    text = me.StringField()
    pre_cot = me.ListField(me.StringField())

class UploadDocument(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    doc_id = me.StringField(required=True)
    user_id = me.StringField(required=True)
    name = me.StringField(required=True)
    file = me.FileField(required=True)
    text = me.StringField(required=True)
    format = me.StringField(required=True)
    create_time = me.StringField(required=True)
    extend_data = me.DictField(default={})

    qa_series_id = me.StringField()
    size = me.FloatField(required=True)
    selected = me.BooleanField(default=True)
    obj_key = me.StringField(required=True)
    analysed = me.BooleanField(default=False)
    analysed_pro = me.BooleanField(default=False)
    pre_cot = me.BooleanField(default=False)

# 用户信息类
class User(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    name = me.StringField(required=True)
    passwd = me.StringField(required=True)
    max_devices = me.IntField(required=True, default=1)
    create_date = me.StringField(required=True)
    expire_date = me.StringField(required=True)
    department = me.StringField()
    real_name = me.StringField()
    phone = me.StringField()
    creator = me.StringField(default='')
    sub_users = me.ListField(me.StringField(), default=[])
    latest_login = me.StringField()
    access_type = me.StringField(required=True, choices=['admin', 'super_admin', 'normal'])
    email = me.StringField(default="")
    remark = me.StringField(default="")
    extend_data = me.DictField(default={})


def init_mongo_connection():
    connection = connect(
        db=CommonConfig['MONGODB']['DB'],
        host=CommonConfig['MONGODB']['Host'],
        port=CommonConfig['MONGODB']['Port'],
        username=CommonConfig['MONGODB']['Username'],
        password=CommonConfig['MONGODB']['Password'],
        authentication_source=CommonConfig['MONGODB']['authDB']
    )
    return connection