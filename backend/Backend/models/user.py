import mongoengine as me


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
