import mongoengine as me

# 删除文件和文件夹类
class DeleteFile(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    user_id = me.StringField(required=True)
    name = me.StringField(required=True)
    text = me.StringField(required=True)
    parent_id = me.StringField(required=True)
    type = me.StringField(required=True)
    create_time = me.StringField(required=True)
    update_time = me.StringField(required=True)
    delete_time = me.StringField(required=True)
    history_version = me.ListField(default=[])
    extend_data = me.DictField(default={})





















