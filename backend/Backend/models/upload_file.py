import mongoengine as me

# 上传稿件类
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
