import mongoengine as me

# 上传稿件类
class Image(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    user_id = me.StringField(required=True)
    name = me.StringField(required=True)
    file = me.FileField(required=True)
    create_time = me.StringField(required=True)
    extend_data = me.DictField(default={})