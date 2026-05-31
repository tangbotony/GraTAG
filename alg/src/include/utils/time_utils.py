import time
import traceback
from datetime import datetime


class TimeCounter:
    def __init__(self):
        self.time_all_tasks_list = dict()
        self.time_all_tasks_dict = dict()

    def add_task(self, task_name: str):
        assert task_name not in self.time_all_tasks_list, "添加了重复的计时器！！！！"
        assert task_name not in self.time_all_tasks_dict, "添加了重复的计时器！！！！"
        self.time_all_tasks_list[task_name] = [time.time()]
        self.time_all_tasks_dict[task_name] = {"start": time.time()}

    def add_time_stone(self, task_name: str, time_stone_name: str = ""):
        assert task_name in self.time_all_tasks_list, "该计时器没有生成！！！！"
        assert task_name in self.time_all_tasks_dict, "该计时器没有生成！！！！"
        task_times = self.time_all_tasks_list[task_name]
        delta_time = 0
        if len(task_times) >= 2:
            delta_time = time.time() - task_times[-1]
        self.time_all_tasks_list[task_name].append(time.time())
        self.time_all_tasks_dict[task_name][time_stone_name] = time.time()
        return delta_time

    def time_since_last_stone(self, task_name: str) -> float:
        assert task_name in self.time_all_tasks_list, "该计时器没有生成！！！！"
        assert task_name in self.time_all_tasks_dict, "该计时器没有生成！！！！"
        task_times = self.time_all_tasks_list[task_name]
        return time.time() - task_times[-1]

    def time_since_specific_stone(self, task_name: str, time_stone_name: str) -> float:
        assert task_name in self.time_all_tasks_list, "该计时器没有生成！！！！"
        assert task_name in self.time_all_tasks_dict, "该计时器没有生成！！！！"
        assert time_stone_name in self.time_all_tasks_dict[task_name], "无效的时间节点索引！！！！"
        task_times = self.time_all_tasks_dict[task_name]
        time_stone_time = task_times[time_stone_name]
        return time.time() - time_stone_time

    def get_task_times(self, task_name: str):
        assert task_name in self.time_all_tasks_list, "该计时器没有生成！！！！"
        assert task_name in self.time_all_tasks_dict, "该计时器没有生成！！！！"
        return self.time_all_tasks_list[task_name], self.time_all_tasks_dict[task_name]


def is_valid_date(date_str, start_or_end_time=None):
    try:
        assert isinstance(date_str, str), "isinstance(date_str, str)"
        if date_str != "":
            try:
                # 尝试按照"yyyy-mm-dd"的格式解析字符串
                datetime.strptime(date_str, '%Y-%m-%d')
                return True, date_str
            except:
                assert start_or_end_time is not None, "start_or_end_time is not None"
                local_vars = {}
                exec(
                    "from datetime import datetime\nfrom datetime import timedelta\n" + date_str,
                    {"NOW_TIME": datetime.now()},
                    local_vars
                )
                datetime.strptime(local_vars[start_or_end_time], '%Y-%m-%d')
                return True,  "from datetime import datetime\nfrom datetime import timedelta\n" + date_str  # 解析成功，返回True
        else:
            return False, ""  # 解析失败，返回False

    except Exception as e:
        print(e)
        print(traceback.print_exc())
        return False, ""  # 解析失败，返回False

def now_date():
    """返回当日日期"""
    now = datetime.now()
    # 格式化日期
    formatted_date = now.strftime("%Y-%m-%d")
    return formatted_date



if __name__ == '__main__':
    local_vars = {}
    exec("""from datetime import datetime
from datetime import timedelta
end_date = NOW_TIME.strftime('%Y-%m-%d')
""", {"NOW_TIME": datetime.now()}, local_vars)
    print(local_vars['end_date'])
