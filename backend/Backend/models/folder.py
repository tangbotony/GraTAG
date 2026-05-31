import mongoengine as me
import datetime

FILE_TYPE_DOCUMENT = "document"
FILE_TYPE_FOLDER = "folder"

# 文件夹类
class Folder(me.Document):
    _id = me.StringField(required=True, primary_key=True)
    name = me.StringField(required=True)
    parent_id = me.StringField(required=True)
    create_time = me.StringField(required=True)
    update_time = me.StringField(required=True)
    is_trash = me.BooleanField(default=False)
    trash_time = me.StringField(default="")
    is_delete = me.BooleanField(default=False)
    extend_data = me.DictField(default={})

# 稿件和文件夹元数据
class FileMeta:
    def __init__(self, file, type):
        self._id = file._id
        self.name = file.name
        self.type = type
        self.parent_id = file.parent_id
        self.create_time = file.create_time
        self.update_time = str(file.update_time)
        self.is_trash = file.is_trash
        self.trash_time = file.trash_time

    def __lt__(self, other):
        return self.update_time > other.update_time if self.type == other.type else self.type > other.type

        




