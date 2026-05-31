import datetime

import mongoengine as me

FUNCTION = "function"
CONTENT = "content"

# 反馈意见类
class Feedback(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    user_id = me.StringField(required=True)
    brief = me.StringField(required=True, default="")
    description = me.StringField(required=True, default="")
    contact = me.StringField(required=True, default="")
    pic_list = me.ListField(me.StringField())
    create_time = me.StringField(required=True)
    type = me.StringField(default=FUNCTION)
    extend_data = me.DictField(default={})