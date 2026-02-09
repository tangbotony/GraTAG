
import mongoengine as me

# 黑名单token
class BlackToken(me.Document):
    jti = me.StringField(required=True)
    type = me.StringField(required=True)
    expireAt = me.DateTimeField(required=True)