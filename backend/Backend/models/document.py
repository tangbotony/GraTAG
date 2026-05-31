import datetime

import mongoengine as me

FILE_TYPE_DOCUMENT = "document"
FILE_TYPE_FOLDER = "folder"


# 历史版本
class HistoryVersion(me.Document):
     version = me.StringField()
     text = me.StringField()
     create_time = me.StringField()

# 稿件类
class Document(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    user_id = me.StringField(required=True)
    name = me.StringField(required=True)
    parent_id = me.StringField(required=True)
    path = me.ListField(required=True)
    text = me.StringField(required=True)
    plain_text = me.StringField(default="")
    editable = me.BooleanField(default=True)
    shared = me.BooleanField(default=False)
    type = me.StringField(required=True)
    create_time = me.StringField(required=True)
    update_time = me.StringField(required=True)
    history_version = me.ListField(default=[])
    is_trash = me.BooleanField(default=False)
    trash_root = me.BooleanField(default=False)
    trash_time = me.StringField(default="")
    is_delete = me.BooleanField(default=False)
    extend_data = me.DictField(default={})
    reference = me.ListField(default=[])
    is_quote = me.BooleanField(default=False)

    meta = {'indexes': [
        {'fields': ['$name'],
         'weights': {'name': 10}
        }
    ]}

# 稿件和文件夹元数据
class FileMeta:
    def __init__(self, file):
        self._id = file._id
        self.name = file.name
        self.type = file.type
        self.parent_id = file.parent_id
        self.create_time = file.create_time
        self.update_time = str(file.update_time)
        self.is_trash = file.is_trash
        self.trash_time = file.trash_time
        self.path = file.path
        

    def __lt__(self, other):
        return self.update_time > other.update_time if self.type == other.type else self.type > other.type