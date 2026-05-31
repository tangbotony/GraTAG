import re
import os
import json
import traceback


def get_date(text):
    # 正则表达式匹配日期
    pattern = r'(\d{4}年\d{1,2}月\d{1,2}日)'

    # 使用 re.search 查找日期
    match = re.search(pattern, text)

    # 如果找到匹配，输出日期
    if match:
        return match.group(1)
    else:
        return ''


if __name__ == '__main__':

    # 指定要遍历的文件夹路径
    folder_path = 'log/ainews/'

    # 定义一个存储结果的列表
    all_results = []

    # 遍历文件夹中的每个文件
    for filename in os.listdir(folder_path):
        # 检查文件是否以 .log 结尾
        if filename.endswith('.log'):
            # 获取文件的完整路径
            file_path = os.path.join(folder_path, filename)

            # 打开并读取当前的 log 文件
            with open(file_path, 'r', encoding='utf-8') as file:
                log_lines = file.readlines()

            # 定义一个存储当前文件结果的列表
            result = []

            # 定义一个临时变量来存储当前的日志块
            current_block = []

            # 遍历所有行
            for line in log_lines:
                # 如果这一行以日期开头，表示是一个新的日志块开始了
                if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}', line):
                    # 如果当前块不为空，检查它是否包含目标内容
                    if current_block:
                        # 将块中的行组合成一个字符串
                        combined_block = ''.join(current_block)
                        # 检查是否包含目标关键词
                        if "最终问题回答 prompt:" in combined_block:
                            result.append(combined_block.strip())
                    # 开始一个新的块
                    current_block = [line]
                else:
                    # 如果没有以日期开头，表示是当前块的延续
                    current_block.append(line)

            # 检查最后一个块
            if current_block:
                combined_block = ''.join(current_block)
                if "最终问题回答 prompt:" in combined_block:
                    result.append(combined_block.strip())

            # 将当前文件的结果加入到总结果中
            all_results.extend(result)

    # 输出所有结果
    all_results_dict = dict()
    all_query_set = set()
    for entry in all_results:
        try:
            question = entry.split("来回答问题。\n\n问题: ")[1]
            question = question.split("补充信息")[0].strip()
            references = entry.split("参考资料：")[1].split("提示思路")[0].strip()
            date = entry.split("补充信息：今天的日期是")[1].split("参考资料：")[0].strip()
            all_query_set.add(question)
            if question not in all_results_dict:
                all_results_dict[question] = list()

            # 使用 '\n资料' 作为分隔符将字符串分割为列表
            reference_list = references.split('\n资料')
            reference_dict = dict()
            for ref_i_index, ref_i in enumerate(reference_list):
                ref_i_content = ref_i.split(":")[1]
                ref_i_title_with_date = ref_i_content.split("：")[0]
                ref_i_pure = ref_i_content.split("：")[1]
                reference_dict[ref_i_index] = {
                    "origin": ref_i,
                    "content": ref_i_pure,
                    "title": ref_i_title_with_date.split('（发布于')[0],
                    "date": get_date(ref_i_title_with_date)
                }
            all_results_dict[question].append({
                "references": reference_dict,
                "date": date
            })
        except:
            traceback.print_exc()

    # 将字典写入 JSON 文件
    with open('log/references_result_raw.json', 'w') as json_file:
        json.dump(all_results_dict, json_file, indent=4, ensure_ascii=False)

