import mongoengine as me


# 用户登录记录类
class LoginHistory(me.Document):
    name = me.StringField(required=True)
    access_token = me.StringField(required=True)
    refresh_token = me.StringField(required=True)
    jti = me.StringField(required=True)
    status = me.IntField(required=True)
    create_time = me.DateTimeField(required=True)
    expire_time = me.DateTimeField(required=True)
