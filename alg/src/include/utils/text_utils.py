import re
import json
import random
import string
import traceback

import requests
from include.logger import log
from langchain_text_splitters import Language
from langchain_text_splitters import RecursiveCharacterTextSplitter
from include.config import CommonConfig
import hashlib
from include.context.QuesionType import QuesionType


# 句子切分，长句切短句
punctuation_marks = ['。', '！', '？', '；']  # 分句的标准切分
punctuation_marks_short = ['，', ',', '...']  # 短句切分 for 严格重复判断逻辑


def convert_text_to_number(text: str):
    new_text = ""
    for char in text:
        if char in "０１２３４５６７８９．％":
            char = chr(ord(char)-65248)
        new_text = new_text + char
    try:
        if not new_text.endswith("%"):
            return eval(new_text)
        else:
            return eval(new_text.strip("%"))/100
    except SyntaxError:
        return None


def get_otherQA_content(
        llm_total_input,
        multihopdag,
        max_words_input,
        mode,
        name="剪裁QA文档",
        is_answer_when_absent_ref='true'  # 是否将答案为空的QA对加入到返回值中
):
    assert mode in ["query_answer", "query_answer_quickpass"]
    max_length = max_words_input - len(llm_total_input)
    # 整合问答信息
    dag_turns = multihopdag.get_turns()[1]
    queries_lis = []
    for sub_group in dag_turns:
        queries_lis.extend(sub_group)

    words = []
    if mode == "query_answer":    # QA全添加模式
        for i, sub_query_i in enumerate(queries_lis):
            sub_answer_json = multihopdag[sub_query_i].answer
            sub_answer_i = sub_answer_json["answer"]
            if is_answer_when_absent_ref == 'true' or sub_answer_i != '':
                words.append(f"\t- 相关问题{str(i + 1)}：{sub_query_i}\n回答：{sub_answer_i}\n")
    else:      # QA只添加Q的模式
        for i, sub_query_i in enumerate(queries_lis):
            words.append(f"\t- 相关问题{str(i + 1)}：{sub_query_i}")
            # # 改成无序号
            # words.append(f"相关问题：{sub_query_i}")

    current_length = 0
    current_part = []
    for word in words:
        current_part.append(word)
        current_length += len(word)
        # 检查是否超出最大长度
        if current_length > max_length:
            log.warning("在{}中，因为token的限制，子问题信息由{}条剪裁为了{}条！！！".format(name, len(words), len(current_part)))
            current_part = current_part[:-1]
            return '\n'.join(current_part)

    return '\n'.join(current_part)


def get_DocQA_content(
        llm_total_input,
        multihopdag,
        max_words_input,
        name="剪裁QA文档",
        **kwargs
):
    doc_mode = kwargs.get('doc_mode')
    is_answer_when_absent_ref = kwargs.get("is_answer_when_absent_ref", 'true')  # 是否将答案为空的QA对加入到返回值中
    max_length = max_words_input - len(llm_total_input)
    # 整合问答信息
    dag_turns = multihopdag.get_turns()[1]
    queries_lis = []
    for sub_group in dag_turns:
        queries_lis.extend(sub_group)

    words = []
    if doc_mode == "DocAnswerMix_FinalAnswer":    # QA全添加模式
        for i, sub_query_i in enumerate(queries_lis):
            sub_answer_json = multihopdag[sub_query_i].answer
            sub_answer_i = sub_answer_json["answer"]
            if is_answer_when_absent_ref == 'true' or sub_answer_i != '':
                words.append(f"相关问题{str(i + 1)}：{sub_query_i}\n回答：{sub_answer_i}\n")
    else:# QA只添加Q的模式
        for i, sub_query_i in enumerate(queries_lis):
            words.append(f"相关问题{str(i + 1)}：{sub_query_i}")

    current_length = 0
    current_part = []
    for word in words:
        current_part.append(word)
        current_length += len(word)
        # 检查是否超出最大长度
        if current_length > max_length:
            log.warning("在{}中，因为token的限制，子问题信息由{}条剪裁为了{}条！！！".format(name, len(words), len(current_part)))
            current_part = current_part[:-1]
            return '\n'.join(current_part)

    return '\n'.join(current_part)



def get_other_content(
        llm_total_input,
        ref_content,
        max_words_input,
        name="剪裁参考文档"
):
    if isinstance(ref_content, list):
        max_length = max_words_input - len(llm_total_input)

        # 将文本按空格拆分为单词列表
        words = ref_content
        current_length = 0
        current_part = []

        for word in words:
            current_part.append(word)
            current_length += len(word)

            # 检查是否超出最大长度
            if current_length > max_length:
                log.warning("在{}中，因为token的限制，证据由{}条剪裁为了{}条！！！".format(name, len(words), len(current_part)))
                current_part = current_part[:-1]
                return '\n'.join(current_part)
                # 如果超出，将当前部分转换为字符串并添加到结果列表
        return '\n'.join(current_part)
    else:
        max_length = max_words_input - len(llm_total_input)

        # 将文本按空格拆分为单词列表
        words = ref_content.split('\n')
        current_length = 0
        current_part = []

        for word in words:
            current_part.append(word)
            current_length += len(word)

            # 检查是否超出最大长度
            if current_length > max_length:
                log.warning("在{}中, 因为token的限制，证据由{}条剪裁为了{}条！！！".format(name, len(words), len(current_part)))
                current_part = current_part[:-1]
                return '\n'.join(current_part)
                # 如果超出，将当前部分转换为字符串并添加到结果列表
        return '\n'.join(current_part)


def get_other_content_sequential(
        llm_total_input,
        ref_content,
        max_words_input,
        raw_description,
        all_ref_items,
        pdf_ids,
        name="剪裁参考文档",
):
    # 创建 description 到 (oss_id, chunk_num) 的映射
    ref_mapping = {item['description']: (item['other_info']['oss_id'], int(item['other_info']['chunk_num'])) for item in
                   all_ref_items}

    # 建立 raw_description 和 ref_content 的一对一映射

    ref_to_raw = dict(zip(ref_content, raw_description))

    max_length = max_words_input - len(llm_total_input)

    # 将文本按空格拆分为单词列表
    current_length = 0
    current_part = []

    # 逐个处理 ref_content，确保长度不超过 max_length
    for sentence in ref_content:
        current_length += len(sentence)
        if current_length > max_length:
            log.warning(
                "在{}中，因为token的限制，证据由{}条剪裁为了{}条！！！".format(name, len(ref_content), len(current_part)))
            break
        current_part.append(sentence)

    def sort_key(sentence):
        description = ref_to_raw.get(sentence)
        info = ref_mapping.get(description)
        return (info[0], int(info[1]))

    sorted_indices = [i for i, _ in sorted(enumerate(current_part), key=lambda x: sort_key(x[1]))]
    # 区分开不同文档的参考资料
    current_part_sorted = [[] for _ in pdf_ids]

    for i, indice in enumerate(sorted_indices):
        text = current_part[indice]
        cleaned_text = '资料{}: '.format(i) + re.sub(r'资料\d+[:：]?', '', text)
        # cleaned_text = text
        raw_text = ref_to_raw.get(text)
        cleaned_text_ossid_idx = ref_mapping.get(raw_text)[0]
        current_part_sorted_idx = pdf_ids.index(cleaned_text_ossid_idx)
        current_part_sorted[current_part_sorted_idx].append(cleaned_text)

    # all_ref_items_sorted = []
    # for current_part_sorted_i in current_part_sorted:
    #     description = ref_to_raw.get(current_part_sorted_i)
    #     for description_i in all_ref_items:
    #         if description_i['description'] == description:
    #             all_ref_items_sorted.append(description_i)
    return current_part_sorted


def stringB2Q(ustring):
    """把字符串半角转全角"""
    usstring_list = list(ustring)
    result_list = []
    for uchar in usstring_list:
        inside_code = ord(uchar)
        if inside_code < 0x0020 or inside_code > 0x7e:  # 不是半角字符就返回原来的字符
            result_list.append(uchar)
        else:
            if inside_code == 0x0020:  # 除了空格其他的全角半角的公式为: 半角 = 全角 - 0xfee0
                inside_code = 0x3000
            else:
                inside_code += 0xfee0
            result_list.append(chr(inside_code))
    return "".join(result_list)


def stringQ2B(ustring):
    """把字符串全角转半角"""
    usstring_list = list(ustring)
    result_list = []
    for uchar in usstring_list:
        inside_code = ord(uchar)
        if inside_code == 0x3000:
            inside_code = 0x0020
        else:
            inside_code -= 0xfee0
        if inside_code < 0x0020 or inside_code > 0x7e:  # 转完之后不是半角字符返回原来的字符
            result_list.append(uchar)
        else:
            result_list.append(chr(inside_code))
    return "".join(result_list)


def stringpartQ2B(ustring):
    """把字符串中数字和字母全角转半角"""
    usstring_list = list(ustring)
    result_list = []
    for uchar in usstring_list:
        need_transfer = False
        # 判断一个unicode是否是全角英文字母
        if (uchar >= u'\uff21' and uchar <= u'\uff3a') or (uchar >= u'\uff41' and uchar <= u'\uff5a'):
            need_transfer = True
        # 判断一个unicode是否是全角数字
        if uchar >= u'\uff10' and uchar <= u'\uff19':
            need_transfer = True
        if uchar == "．":
            need_transfer = True
        if need_transfer:
            inside_code = ord(uchar)
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xfee0
            if inside_code < 0x0020 or inside_code > 0x7e:  # 转完之后不是半角字符返回原来的字符
                result_list.append(uchar)
            else:
                result_list.append(chr(inside_code))
        else:
            result_list.append(uchar)
    return "".join(result_list)


def get_length_bin(output_string_len):
    """
    长度分箱
    :param output_string_len:
    :return:
    """
    if 0 <= output_string_len <= 10:
        return 10
    elif 10 < output_string_len < 100:
        return round(output_string_len, -1)  # 近似到最接近的十位
    else:
        return round(output_string_len, -2)  # 近似到最接近的百位


def clean_text(char):
    return char.replace("\r", " ").replace("\u3000", " ").replace("\n", " ").strip()


def separate_paragraph(paragraph, length=40, short_priority=True, is_langchain=False):
    if is_langchain:
        chunk_size = length
        chunk_overlap = int(chunk_size * 0.25)
        python_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        result = python_splitter.split_text(paragraph)
        return result

    pattern = r'\s*([，。！？；：“”‘’,.!?;:])\s*'
    paragraph = re.sub(pattern, r'\1', paragraph)
    if short_priority:
        sentences = []
        sentence = ""
        for char in paragraph:
            sentence += char
            # 虽然完整的句子还没有结束，但是短句的长度已经足够长，也要切分
            if char in punctuation_marks_short and len(sentence) >= length:
                sentences.append(sentence)
                sentence = ""
            # 完整的句子结束、切分
            elif char in punctuation_marks:
                # 忽略极其短的句子
                if len(sentence) >= 3:
                    sentences.append(sentence)
                sentence = ""
        # 最后的没有切完的部分也要加上
        if sentence:
            sentences.append(sentence)
        return sentences
    else:
        """
        Splits a Chinese text into segments of approximately 100 characters.
        It uses punctuation marks like period, exclamation mark, and question mark for primary splits.
        Longer sentences are further split using commas and semicolons.
        Short sentences are merged to reach the desired length.
        """
        # Split by sentence-ending punctuation
        sentences = re.split(r'([。!！？?\n])', paragraph)

        # Merge the punctuation back into the sentences
        sentences = [sentences[i] + sentences[i + 1] for i in range(0, len(sentences) - 1, 2)]

        # Function to further split long sentences
        def split_long_sentence(sentence, max_length):
            # Split using commas and semicolons if sentence is too long
            if len(sentence) > max_length:
                return re.split(r'([，,；;])', sentence)
            return [sentence]

        # Split long sentences and merge short sentences
        result = []
        temp_sentence = ''
        for sentence in sentences:
            if len(temp_sentence) + len(sentence) <= length:
                # Merge with the temporary sentence if the total length is within limit
                temp_sentence += sentence
            else:
                # Split the long sentence
                sub_sentences = split_long_sentence(sentence, length)
                for sub_sentence in sub_sentences:
                    if len(temp_sentence) + len(sub_sentence) > length:
                        # Add the temporary sentence to the result if it's long enough
                        if temp_sentence:
                            result.append(temp_sentence)
                            temp_sentence = ''
                        # Add the sub-sentence if it's long enough, otherwise add to temp
                        if len(sub_sentence) > length:
                            result.extend(split_long_sentence(sub_sentence, length))
                        else:
                            temp_sentence = sub_sentence
                    else:
                        # Merge with the temporary sentence
                        temp_sentence += sub_sentence

        # Add the last remaining sentence
        if temp_sentence:
            result.append(temp_sentence)

        return result


def calculate_english_ratio(sentence):
    chinese_count = 0
    english_count = 0
    for char in sentence:
        if '\u4e00' <= char <= '\u9fff':
            chinese_count += 1
        elif 'A' <= char.upper() <= 'Z':
            english_count += 1
        elif '1' <= char.upper() <= '9' or char.upper() == '0':
            english_count += 1
    total_count = chinese_count + english_count
    if total_count == 0:
        return 0
    english_ratio = english_count / total_count
    return english_ratio


def get_search_keywords(raw_text):
    raw_text = raw_text[:3000]
    payload = json.dumps({
        "s": [
            raw_text
        ]
    })
    headers = {
        "token": CommonConfig['AUTH_CONFIG']['key'],
        'Content-Type': 'application/json',
        "Authorization": CommonConfig['NER']["Authorization"]
    }

    res_temp = requests.request("POST", CommonConfig['NER']["keyword_url"],
                                headers=headers, data=payload, timeout=5)
    all_res_json = res_temp.json()[0]
    return all_res_json


def poly_union(current_page, new_page, current_poly, new_poly):
    def poly_union_on_the_same_page(*args):
        assert all([len(each) == 4 for each in args])
        args = list(args)
        if [0, 0, 0, 0] in args:
            args.remove([0, 0, 0, 0])
        return [
            min([each[0] for each in args]),
            min([each[1] for each in args]),
            max([each[2] for each in args]),
            max([each[3] for each in args]),
        ]

    if current_poly == [0, 0, 0, 0]:
        return new_page, new_poly
    if current_page == new_page:
        return current_page, poly_union_on_the_same_page(current_poly, new_poly)
    else:
        if isinstance(current_page, list):
            if new_page not in current_page:
                return current_page.append(new_page), current_poly.append(new_poly)
            else:
                current_poly[current_page.index(new_page)] = poly_union_on_the_same_page(
                    current_poly[current_page.index(new_page)], new_poly)
                return current_page, current_poly
        else:
            return [current_page, new_page], [current_poly, new_poly]


def generate_random_string(input_string: str, length: int):
    characters = string.ascii_letters + string.digits
    num_characters = len(characters)

    # 计算字符串的哈希值
    hash_object = hashlib.sha256(input_string.encode('utf-8', 'ignore'))
    hash_hex = hash_object.hexdigest()

    # 将哈希值转换为一个较长的整数
    hash_int = int(hash_hex, 16)

    # 生成固定长度的编码
    encoded_string = ''
    for _ in range(length):
        index = hash_int % num_characters
        encoded_string += characters[index]
        hash_int //= num_characters

    return encoded_string


# 判定某段字符是json格式
def is_json(myjson):
    try:
        json_object = json.loads(myjson)
        return True
    except:
        return False

def get_md5(s):
    md = hashlib.md5()
    md.update(s.encode('utf-8', errors="ignore"))
    return md.hexdigest()

def is_digit(character):
    return character.isdigit()

def longest_common_substring(A, B):
    # 找到两个字符串的最长公共子串
    m, n = len(A), len(B)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_len = 0
    end_pos = 0

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if A[i - 1] == B[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                if dp[i][j] > max_len:
                    max_len = dp[i][j]
                    end_pos = i

    return A[end_pos - max_len:end_pos]

def replace_multi_line_break(text):
    # 正则表达式匹配两个以上的换行符
    pattern = re.compile(r'(\n\s*){2,}')

    # 替换所有匹配到的换行符为一个换行符
    replaced_text = pattern.sub(r'\n', text)
    return replaced_text


def find_duplicates(combined_list):
    # 使用字典来记录每个元素的出现次数
    from collections import Counter

    # 计算每个元素出现的次数
    element_count = Counter(combined_list)

    # 找到出现次数大于1的元素
    duplicates = [element for element, count in element_count.items() if count > 1]

    return duplicates

def question_type(question):
    question_level = QuesionType.GENERAL
    keywords = ["行程", "考察几次", "多少次","几次","考察情况", "新闻", "近期"]
    if any(keyword in question for keyword in keywords):
        question_level = QuesionType.REAL_TIME
    print("question:{}, question_level:{}".format(question,question_level.value))
    return question_level


def validate_and_filter_codes(text):
    text_origin = text
    # 正则表达式匹配超过六位的编码XXXXXXX并包含前后的中括号
    pattern = re.compile(r'([A-Za-z0-9]{6,})')
    matches = list(pattern.finditer(text))

    # 逆序处理，以免影响后续位置
    for match in reversed(matches):
        start, end = match.span()

        # 判断编码是否被[]紧紧包围
        if start > 0 and end < len(text) and text[start - 1] == '[' and text[end] == ']':
            continue  # 被[]包围的编码保留
        else:
            # 左侧处理：从 start 往前移除空格、【、[ 直到遇到其他字符
            left_idx = start - 1
            left_has_bracket = False
            while left_idx >= 0 and text[left_idx] in ' [【':
                if text[left_idx] in '[【':
                    left_has_bracket = True
                left_idx -= 1

            # 右侧处理：从 end 往后移除空格、】、] 直到遇到其他字符
            right_idx = end
            right_has_bracket = False
            while right_idx < len(text) and text[right_idx] in ' ]】':
                if text[right_idx] in ']】':
                    right_has_bracket = True
                right_idx += 1

            # 删除不符合要求的编码及其前后的空格和特定符号
            if left_has_bracket or right_has_bracket:
                text = text[:left_idx + 1] + text[right_idx:]

    # 移除多余的空格和标点符号
    text = re.sub(r'\s+', ' ', text).strip()
    if text_origin.strip() != text.strip():
        log.warning("text_origin != text!! text origin: {} text: {}".format(text_origin, text))
    lines = text.split('\n')

    # 修正markdown格式内的空格
    def merge_hashes(sentence):
        words = sentence.split()
        combined_hashes = ""
        rest_of_sentence = ""
        first_non_hash_found = False

        for word in words:
            if word.startswith("#") and not first_non_hash_found:
                combined_hashes += word
            else:
                if not first_non_hash_found:
                    rest_of_sentence += " " + word
                    first_non_hash_found = True
                else:
                    rest_of_sentence += " " + word

        return combined_hashes + rest_of_sentence

    res_text = ''
    for line in lines:
        corrected_line = merge_hashes(line)
        res_text += corrected_line + '\n'
    return res_text.strip()


def process_text(text):
    try:
        # 匹配数值和百分比，或者只包含5个字符以内的短句（常见于表格行）
        table_pattern = r'(-?\d+\.?\d*%?|\b\w{1,5}\b)'

        # 逐行处理文本
        lines = text.splitlines()
        processed_lines = []

        for line in lines:
            # 去掉前后的空白符
            clean_line = line.strip()

            # 检查是否符合表格的模式
            if re.fullmatch(table_pattern, clean_line):
                # 如果是表格行（符合数值、百分比或者短句），保留原样
                processed_lines.append(clean_line)
            else:
                # 如果不是表格行，则去掉换行符并拼接成连贯句子
                processed_lines.append(re.sub(r'\s+', ' ', clean_line))

        # 将所有行连接成一个整体，确保文本的连续性
        processed_text = ' '.join(processed_lines).strip()
    except:
        return ""
    return processed_text


def find_original_content(str1, str2, list3):
    # 去掉str1多余的空格和换行符以匹配str2的格式
    clean_str1 = ' '.join(str1.split())
    clean_str2 = ' '.join(str2.split())

    list_final = []

    for item in list3:
        try:
            # 从list3中提取chunk
            chunk_data = json.loads(item[1])
            chunk = chunk_data['chunk']

            # 清理chunk, 保证和str2格式一致
            clean_chunk = ' '.join(chunk.split())

            # 在str2中查找chunk的开始位置
            start_idx = clean_str2.find(clean_chunk)

            if start_idx != -1:
                # 找到对应的str1片段，通过去除多余的空格和换行符进行匹配
                original_content = find_in_str1(str1, clean_chunk)
            else:
                # 如果没有找到匹配，返回空
                original_content = ""

            # 构建新的条目，将原始内容添加到list3的元素中
            new_item = item + [{"origin_content": f"{original_content.strip()}"}]
            list_final.append(new_item)
        except:
            item += [{'origin_content': ''}]
            list_final.append(item)

    return list_final


def find_in_str1(str1, clean_chunk):
    # 使用正则表达式匹配chunk的每个部分，并忽略str1中的换行符和多余的空格
    chunk_words = clean_chunk.split()

    # 构造正则表达式，确保在str1中忽略空格和换行符进行匹配
    pattern = r'\s*'.join(re.escape(word) for word in chunk_words)

    # 在str1中找到第一个匹配的内容
    match = re.search(pattern, str1, re.DOTALL)

    if match:
        # 返回在str1中的原始片段
        return match.group(0)
    else:
        return ""


def map_sentences(original_text):
    # 将原始文本按行分割
    lines = original_text.splitlines()
    sentence_map = {}

    for i, line in enumerate(lines):
        # 去掉前后空白和换行符
        clean_line = line.strip()
        if clean_line:
            # 将原句映射到处理后的句子中
            sentence_map[f"Original Line {i + 1}"] = clean_line

    return sentence_map


if __name__ == '__main__':
    original_text = """请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 1 - 
      
 
 
证券研究报告 
分析师 
 
段超 
S0190516070004 
卓泓 
S0190519070002 
王笑笑 
S0190521100001 
王轶君 
S0190513070008 
彭华莹 
S0190522100002 
郑兆磊
（金工） 
S0190520080006 
占康萍
（金工） 
S0190522070008 
研究助理 
 
金淳 
于长馨 
王祉凝 
谢智勇 
 
 
 
 
“外乱内稳”下的资产配置 
——《宏观大类资产配置手册》第二十八期 
2024 年5 月8 日 
 
投资要点 
本报告为我们推出的大类资产配置新系列报告《宏观大类资产配置手册》的第二十八期。该系列报告将宏
观判断和资产配置量化模型相结合，在宏观环境发生变化的时候为投资者提供大类资产配置建议。 
• 
下一阶段的宏观主题。内稳：当前中国经济结构性企稳、外需持续改善，后续在政治局会议精神的
指导下经济或将持续回升。外乱：外部地缘风险持续，当前我们可能并不处在一个所谓典型的“朱
格拉周期”，即需求大幅扩张或技术革新带来的投资周期。而供给端的因素，尤其是资源供给方面
的供给“割裂”一方面增加了供给端的不确定性，另一方面又反过来推升全球对于战略重要部门的
投资增长。 
• 
下一阶段大类资产配置的建议。短期看，中国经济内需企稳，外需持续改善，政策呵护仍有空间；
中期看，全球地缘紧张局势延续焦灼态势；“外乱内稳”环境下，海外资金有流入中国市场的空
间。对下一阶段大类资产配置的展望：大盘股>黄金>工业品>农产品>中盘股>小盘股>利率债>信用
债>现金。 
• 
量化模型的资产配置建议。本次报告在文中阐述了资产配置模型的设计流程思路，给出了战略配置
参考组合和动态战术组合建议，立足于长期投资、多元分散化投资理念，我们分别为不同风险偏好
投资者构建了保守、稳健和积极三种风险等级的配置组合权重建议。 
 
 
下阶段 大类资产配置建议 
组合
类型 
沪深
300 
中证
500 
中证
1000 
利率
债 
信用
债 
工业
品期
货 
农产
品期
货 
实物
黄金 
保守 
7.4% 
8.0% 
6.5% 
24.6
% 
24.6
% 
4.7% 
2.1% 
22.0
% 
稳健 
13.7
% 
13.7
% 
6.8% 
4.0% 
4.0% 
6.0% 
3.0% 
49.0
% 
积极 
17.3
% 
17.3
% 
8.7% 
1.5% 
1.5% 
4.0% 
2.0% 
48.9
% 
 
注：左图绿色区域的边缘为中性，在绿色区域内部为低配；右图每行相加不完全等于100%，主因四舍五入误差。 
数据来源：兴业证券经济与金融研究院 
• 
风险提示：1）地缘政治风险；2）海外宏观环境超预期变化；3）模型失效风险 
-
-
-
大盘股
中盘股
小盘股
利率债
信用债
工业大宗
农产品
黄金
现金
下阶段宏观大类资产配置建议
宏
观
经
济 
 
宏
观
大
类
资
产
配
置  
 
本报告仅供：西南证券股份有限公司 盛宝丹 使用，已记录日志请勿传阅。
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 2 - 
 
目录 
内稳：中国经济结构性企稳、外需改善 ................................................................- 4 - 
经济结构性企稳，政策发力仍有空间 ................................................................ - 5 - 
外需环境持续改善 ................................................................................................ - 9 - 
外乱：全球地缘风险下的供需变化 ......................................................................- 14 - 
全球来看，地缘冲突持续处于高位 .................................................................. - 15 - 
“外乱内稳”下的大类资产配置 ...............................................................................- 20 - 
资产配置建议的量化方案 ......................................................................................- 26 - 
政策设定与资产划分 .......................................................................................... - 27 - 
战略资产配置组合 .............................................................................................. - 28 - 
战术资产配置组合 .............................................................................................. - 32 - 
图表标题 
图表1：一季度经济回升动能增强 
- 5 - 
图表 2：基数影响下，中游设备投资增速下滑，两年复合增速整体持平 
- 5 - 
图表 3：3 月国内挖掘机销量同比增速也有所回升 
- 6 - 
图表4：2024 年4 月政治局会议与前期相关会议对比 
- 7 - 
图表5：后续，专项债发行可能提速，2024 年超长期特别国债可能也将进入项目报
审期+国债发行期 
- 9 - 
图表6：从出口产品端来看，2024Q1 中国出口的主要拉动来自于交运设备、电子、
家电和部分资本品 
- 10 - 
图表7：一季度中国对各经济体出口增速普遍回升 
- 10 - 
图表 8：美国一季度经济增速走“弱”的背后是进口增加，消费仍保持韧性 
- 11 - 
图表9：美国名义库存增速见底回升，实际库存增速震荡回升 
- 11 - 
图表10：美国制造商的交运设备、金属制品、纺织轻工和能源品库存增速上行- 11 - 
图表11：新兴经济体是中国工程机械需求的主要拉动 
- 12 - 
图表12：2023 年下半年开始，一带一路对中国的资本品需求显著强于其他商品- 12 
- 
图表13：综合出口回升速度来看，新优势产业和电子家电等制造业或更加受益- 13 - 
图表 14：全球地缘冲突不断 
- 15 - 
图表 15：美国国防与航天工业设备生产指数已创历史新高 
- 15 - 
图表 16：北约军费快速增长 
- 16 - 
图表 17：全球资源禀赋不均衡，大宗商品产地集中度高，尤其是新能源金属- 16 - 
图表 18：对大宗商品的贸易干预数量持续增加，俄乌冲突后进一步加剧 
- 17 - 
图表 19：地缘风险持续演绎，对大宗商品供给“割裂”的担忧明显升温 
- 17 - 
图表 20：2023 年全球投资占GDP 比重以及跨境绿地投资继续处于高位 
- 18 - 
图表 21：2023 年的全球绿地投资依然集中在战略重要性的行业 
- 18 - 
图表 22：全球资源获取诉求再次上升 
- 19 - 
图表 23：资源型经济体资本形成占GDP 的比重 
- 19 - 
图表24：从股债对比角度看，权益资产的相对性价比在上升 
- 21 - 
图表 25：近期资本市场相关政策部署情况 
- 22 - 
图表 26：2023 年以来，A 股权益资产对中国制造优势的定价有明显低估 
- 23 - 
图表 27：2024 年以来，商品表现有所分化，有色和贵金属涨幅较大 
- 23 - 
图表 28：大宗有色和黑色从2023 年8 月以来走背，2024 年4 月再次同步 - 24 - 
图表 29：2024 年金价的上涨主要是由于非宏观基本面因素贡献的 
- 24 - 
图表 30：2023 年以来，铜价或已脱离原本的经济框架，进入新轨道 
- 25 - 
图表31：资产配置流程示意 
- 27 - 
图表32：风险资产长期预期收益分析框架 
- 29 - 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 3 - 
图表 33：南华工业品商品期货收益分析 
- 29 - 
图表 34：各类细分资产中长期收益率预测值（预测日20240430） 
- 30 - 
图表35：大类资产长期收益风险预测结果 
- 30 - 
图表36：不同风险目标下大类资产战略配置参考组合配置建议 
- 31 - 
图表37：不同风险等级的大类资产战略配置参考组合 
- 31 - 
图表38：不同风险等级的细分资产战略配置参考组合 
- 31 - 
图表39：各类资产未来季度波动率预测 
- 32 - 
图表40：各资产配置建议 
- 33 - 
  
 
 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 4 - 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
内稳：中国经济结构性企稳、外需改善 
当前中国经济结构性企稳，后续政策落地或将呵护经济持续回升。未来一段时间
内外需均有继续修复的空间：一是中国2024 年广义财政的扩张趋势已定，后续存
量工具落地或将加快；二是外需存在持续改善空间。 
 
 
 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 5 - 
 
经济结构性企稳，政策发力仍有空间 
 
当前中国经济结构性企稳，后续政策落地或将呵护经济持续回升 
• 
当前经济企稳修复，其中新动能持续推进。一季度GDP 增速超预期，结构
上看，新旧动能持续切换。生产端，制造业和高技术产业增加值同比增速
延续走高，高技术产业增加值增速仍高于整体。需求端，设备更新改造持
续推进，一季度固定资产投资当中设备器具购置同比增速明显走高，中游
设备投资增速仍高于整体，国内挖掘机销量增速也有所回升；而旧动能方
面，一季度地产开发投资降幅先收窄后又走阔，同时资金来源端持续承
压，地产部门延续调整。 
• 
后续政策持续推进落地，或将呵护经济回升势头。一季度经济修复的结构
性特征较为明显，新旧动能结构分化之下，工业企业供需环境弱化（一季
度季调后产能利用率下降），居民消费信心虽回升但仍偏低，GDP 平减指
数仍在收缩，经济的持续修复仍需要政策落地呵护。向后看，考虑到存量
财政工具仍然充裕，后续或将进入加速推进使用期，经济企稳回升的势头
或有望延续。 
 
图表1：一季度经济回升动能增强 
 
 
 
注：2021 年、2023 年为两年复合同比增速；2015-2023Q4 均值为剔除2020 年Q1 结果。 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
图表 2：基数影响下，中游设备投资增速下滑，两年复合增速整体持平 
 
 
 
注1：2021 年为两年复合同比增速； 
注2：中游设备包含通用设备、专用设备、电气机械和器材三个行业。 
数据来源：CEIC，兴业证券经济与金融研究院整理 
0.6 
-2.1 
4.0 
0.6 
2.1 
0.6 
1.5 
1.0 
1.6 
1.0 
1.5 
-3.0
-2.0
-1.0
0.0
1.0
2.0
3.0
4.0
5.0
中国实际GDP环比季调，%
-50.0
-40.0
-30.0
-20.0
-10.0
0.0
10.0
20.0
30.0
40.0
50.0
13
14
15
16
17
18
19
20
21
22
23
24
制造业投资，当月同比增速，%
中游设备投资，当月同比增速，%
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 6 - 
 
图表 3：3 月国内挖掘机销量同比增速也有所回升 
 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
政治局会议强调稳增长部署，以巩固和增强经济回升向好态势 
• 
4 月政治局会议强调和侧重稳增长部署。短期经济工作方面，4 月份政治局
会议研判经济形势，强调“国内大循环不够顺畅”；在经济工作要求方
面，提出“坚持乘势而上，避免前紧后松，切实巩固和增强经济回升向好
态势”。这些都体现了顶层部署对于短期稳增长工作态度积极，要求乘势
而上、继续发力。 
• 
稳增长的三方面抓手：宏观政策靠前、扩内需更加重要、防风险新增稳定
考虑。 
 
宏观政策靠前发力，财政政策强调落地存量，货币政策有增量表态。
会议强调“要靠前发力有效落实已经确定的宏观政策”。财政政策方
面，强调存量工具使用落地，要求“要及早发行并用好超长期特别国
债，加快专项债发行使用进度”，后续财政节奏可能加快；货币政策
方面，强调“要灵活运用利率和存款准备金率等政策工具，加大对实
体经济支持力度”，后续降准、降息可期。 
 
扩内需工作更靠前，不仅涉及已有政策落地，还有内需空间的培育。
不同于2023 年4 月和2023 年12 月政治局会议首先部署产业发展相关
工作，本次会议首先部署“积极扩大国内需求”。在扩内需工作部署
方面，不仅有已有政策的落地安排，强调落实好大规模设备更新和消
费品以旧换新行动方案；还有消费、投资相关增量工作谋划，提出创
造更多消费场景、深入推进以人为本的新型城镇化、实施好PPP 机制
充分激发民间投资活力。 
 
防风险新增稳定考虑，地产消化存量、化债兼顾发展、资本市场健康
发展。本次会议在部署房地产、化债、金融等相关重点领域风险防范
和改革发展工作方面，更加突出稳定相关考虑。房地产方面，除了延
续因城施策、保交楼相关部署，新增部署“统筹研究消化存量房产和
优化增量住房的政策措施”，指向政策关注解决地产销售走低下的库
存压力问题。化债方面，强调“确保债务高风险省份和市县既真正压
降债务、又能稳定发展”，化债工作更加兼顾发展。金融领域，新增
部署“多措并举促进资本市场健康发展”，这也是继前期一系列部署
后，顶层决策对资本市场的持续关注和聚焦，也反映资本市场持续受
到政策重视和关注。 
-100%
-50%
0%
50%
100%
150%
200%
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
挖掘机销量当月同比增速3MMA
国内
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 7 - 
图表4：2024 年4 月政治局会议与前期相关会议对比 
 
2024 年4 月政治局会议 
2023 年12 月政治局会议 
2023 年4 月政治局会议 
三中全
会相关 
决定今年7月在北京召开中国共产党第二十届
中央委员会第三次全体会议。 
 
改革开放是党和人民事业大踏步赶上时代的
重要法宝。当……全党必须自觉把改革摆在
更加突出位置，紧紧围绕推进中国式现代化
进一步全面深化改革。 
 
……，以经济体制改革为牵引，以促进社会
公平正义、增进人民福祉为出发点和落脚
点，更加注重系统集成，更加注重突出重
点，更加注重改革实效，推动生产关系和生
产力、上层建筑和经济基础、国家治理和社
会发展更好相适应，为中国式现代化提供强
大动力和制度保障。 
/ 
/ 
经济 
形势 
经济运行中积极因素增多，动能持续增强，
社会预期改善，高质量发展扎实推进，呈现
增长较快、结构优化、质效向好的特征，经
济实现良好开局。 
经济持续回升向好仍面临诸多挑战，主要是
有效需求仍然不足，企业经营压力较大，重
点领域风险隐患较多，国内大循环不够顺
畅，外部环境复杂性、严峻性、不确定性明
显上升。 
我国经济回升向好，高质量发展扎实推
进，现代化产业体系建设取得重要进展，
科技创新实现新的突破，改革开放向纵深
推进，安全发展基础巩固夯实，民生保障
有力有效，全面建设社会主义现代化国家
迈出坚实步伐。 
我国疫情防控取得重大决定性胜利，经济
社会全面恢复常态化运行，宏观政策靠前
协同发力，需求收缩、供给冲击、预期转
弱三重压力得到缓解，经济增长好于预
期，市场需求逐步恢复，经济发展呈现回
升向好态势，经济运行实现良好开局。 
当前我国经济运行好转主要是恢复性的，
内生动力还不强，需求仍然不足，经济转
型升级面临新的阻力，推动高质量发展仍
需要克服不少困难挑战。 
政策 
思路 
坚持稳中求进工作总基调，完整、准确、全
面贯彻新发展理念，加快构建新发展格局，
着力推动高质量发展，坚持乘势而上，避免
前紧后松，切实巩固和增强经济回升向好态
势。 
坚持稳中求进工作总基调……加大宏观调
控力度，统筹扩大内需和深化供给侧结构
性改革，统筹新型城镇化和乡村全面振
兴，统筹高质量发展和高水平安全，切实
增强经济活力、防范化解风险、改善社会
预期，巩固和增强经济回升向好态势…… 
坚持稳中求进工作总基调，完整、准确、
全面贯彻新发展理念，加快构建新发展格
局，全面深化改革开放，…… 
宏观 
政策 
要靠前发力有效落实已经确定的宏观政策，
实施好积极的财政政策和稳健的货币政策。 
坚持稳中求进、以进促稳、先立后破，强
化宏观政策逆周期和跨周期调节，继续实
施积极的财政政策和稳健的货币政策 
积极的财政政策要加力提效，稳健的货币
政策要精准有力，形成扩大需求的合力。 
财政 
政策 
要及早发行并用好超长期特别国债，加快专
项债发行使用进度，保持必要的财政支出强
度，确保基层“三保”按时足额支出。 
积极的财政政策要适度加力、提质增效 
/ 
货币 
政策 
要灵活运用利率和存款准备金率等政策工
具，加大对实体经济支持力度，降低社会综
合融资成本。 
稳健的货币政策要灵活适度、精准有效 
/ 
扩大 
内需 
要积极扩大国内需求，落实好大规模设备更
新和消费品以旧换新行动方案。要创造更多
消费场景，更好满足人民群众多样化、高品
质消费需要。要深入推进以人为本的新型城
镇化，持续释放消费和投资潜力。要实施好
政府和社会资本合作新机制，充分激发民间
投资活力。 
要着力扩大国内需求，形成消费和投资相
互促进的良性循环 
恢复和扩大需求是当前经济持续回升向好
的关键所在。积极的财政政策要加力提
效，稳健的货币政策要精准有力，形成扩
大需求的合力。要多渠道增加城乡居民收
入，改善消费环境，促进文化旅游等服务
消费。要发挥好政府投资和政策激励的引
导作用，有效带动激发民间投资。 
产业 
发展 
要因地制宜发展新质生产力。要加强国家战
略科技力量布局，培育壮大新兴产业，超前
布局建设未来产业，运用先进技术赋能传统
产业转型升级。 
要以科技创新引领现代化产业体系建设，
提升产业链供应链韧性和安全水平。 
要加快建设以实体经济为支撑的现代化产
业体系，既要逆势而上，在短板领域加快
突破，也要顺势而为，在优势领域做大做
强。要夯实科技自立自强根基，培育壮大
新动能。要巩固和扩大新能源汽车发展优
势，加快推进充电桩、储能等设施建设和
配套电网改造。要重视通用人工智能发
展，营造创新生态，重视防范风险。 
资本 
市场 要积极发展风险投资，壮大耐心资本。 
/ 
/ 
深化 
改革 
要坚定不移深化改革扩大开放，建设全国统
一大市场，完善市场经济基础制度。 
要深化重点领域改革，为高质量发展持续
注入强大动力 
/ 
对外 
开放 
要积极扩大中间品贸易、服务贸易、数字贸
易、跨境电商出口，支持民营企业拓展海外
市场，加大力度吸引和利用外资。 
要扩大高水平对外开放，巩固外贸外资基
本盘 
要全面深化改革、扩大高水平对外开
放。……要把吸引外商投资放在更加重要
的位置，稳住外贸外资基本盘。要支持有
条件的自贸试验区和自由贸易港对接国际
高标准经贸规则，开展改革开放先行先
试。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 8 - 
风险 
防范 
要持续防范化解重点领域风险。……要深入
实施地方政府债务风险化解方案，确保债务
高风险省份和市县既真正压降债务、又能稳
定发展。要持续推动中小金融机构改革化
险，多措并举促进资本市场健康发展。 
要持续有效防范化解重点领域风险，坚决
守住不发生系统性风险的底线。 
要有效防范化解重点领域风险，统筹做好
中小银行、保险和信托机构改革化险工
作。……要加强地方政府债务管理，严控
新增隐性债务。 
房地 
产 
继续坚持因城施策，压实地方政府、房地产
企业、金融机构各方责任，切实做好保交房
工作，保障购房人合法权益。要结合房地产
市场供求关系的新变化、人民群众对优质住
房的新期待，统筹研究消化存量房产和优化
增量住房的政策措施，抓紧构建房地产发展
新模式，促进房地产高质量发展。 
/ 
要坚持房子是用来住的、不是用来炒的定
位，因城施策，支持刚性和改善性住房需
求，做好保交楼、保民生、保稳定工作，
促进房地产市场平稳健康发展，推动建立
房地产业发展新模式。在超大特大城市积
极稳步推进城中村改造和“平急两用”公
共基础设施建设。规划建设保障性住房。 
 
数据来源：共产党员网，兴业证券经济与金融研究院整理 
 
往后看，财政加码增量仍有空间 
• 
2024 年年初以来，财政节奏稳健，后续存量工具使用可能加快。2024 年一
季度，货币政策降准降息超预期落地，财政存量工具落地节奏稳健，后续
财政宽松仍有空间。具体而言，2023 年增发的万亿国债年初以来持续推进
落地，发改委表示将推动所有增发国债项目于今年6 月底前开工建设；
2024 年地方专项债前期可能受限于项目，发行进度偏慢，4 月下旬项目筛
选完成，后续专项债发行可能将提速；2024 年超长期特别国债尚未发行，
专项用于国家重大战略实施和重点领域安全能力建设，发改委4 月17 日表
示已经研究起草了相关行动方案，经过批准同意后即开始组织实施。向后
看，2023 年增发的万亿国债可能将进一步推进形成实物工作量，2024 年专
项债发行可能提速，2024 年超长期特别国债可能也将进入项目报审期+国
债发行期。 
• 
财政加码增量仍有空间。考虑到当前财政存量工具仍在使用，且去年二季
度经济低基数，今年二季度经济增速目标压力或不大。但当前宏微观仍存
在一些感知差，市场对财政加码可能仍有期待。是否会有增量工具的观察
时点可能在7 月二季度经济数据出炉之后，关注7 月底的政治局会议。从
可能的工具来看，近年来财政方面动用的工具包括增发国债、动用地方债
结存限额、为结构性货币政策工具贴息等，准财政方面包括PSL 提额、设
立政策性开发性金融工具、发放政策行专项借款等。如果后续稳增长诉求
抬升，财政加码也仍有空间。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 9 - 
图表5：后续，专项债发行可能提速，2024 年超长期特别国债可能也将进入项目报审期+国债发行期 
 
2023 年增发国债 
2024 年超长期特别国债 
地方专项债 
投向 
灾后恢复重建（超过2000 亿元） 
国家重大战略实施和重点领域安全
能力建设： 
交通基础设施 
重点防洪治理工程（超过5000 亿元） 
高水平科技自立自强 
能源 
自然灾害应急能力提升工程 
城乡融合发展 
农林水利 
其他重点防洪工程 
区域协调发展 
生态环保 
灌区建设改造和重点水土流失治理工程 
粮食和能源资源安全 
社会事业 
城市排水防涝能力提升行动 
人口高质量发展 
城乡冷链等物流基础设施 
重点自然灾害综合防治体系建设工程 
美丽中国建设 
市政和产业园区基础设施 
东北地区和京津冀受灾地区等高标准农
田建设 
国家重大战略领域 
保障性安居工程（城镇老旧小区改造、保障性
租赁住房、公共租赁住房、棚户区改造、城中
村改造、保障性住房） 
新型基础设施 
新能源 
进度 
资金：截至2024 年2 月，增发国债资金
已经全部落实到1.5 万个具体项目。 
 
项目：截至2024 年2 月，发展改革委已
经分三批下达完毕1 万亿元增发国债项
目清单。 
 
开工：据悉，截至3 月下旬，北京市、
河北省的项目开工率分别达到了48%、
45%。（要求：推动所有增发国债项目于
2024 年6 月底前开工建设。） 
资金：尚未发行（截至
2024.4.24） 
 
项目：目前发改委会同有关方面已
经研究起草了支持国家重大战略和
重点领域安全能力建设的行动方
案，经过批准同意后即开始组织实
施。 
资金：发行进度偏慢。截至2024.4.30，新增专
项债发行进度为18.5%，明显低于近五年同期均
值的30.4%。 
 
项目：4 月下旬，项目筛选完成。2 月初监管部
门组织地方申报2024 年第一批专项债项目，2
月底之前地方已上报，3 月底监管尚未反馈审核
结果；4 月中旬，发改委完成项目初筛，推送给
财政部并反馈给各地方，财政部正在对项目融
资收益平衡等进行审核；4 月下旬，项目筛选完
成，共筛选通过专项债券项目约3.8 万个、
2024 年专项债券需求5.9 万亿元左右。 
 
数据来源：中国政府网，国新办，21 世纪经济报道，Wind，兴业证券经济与金融研究院整理 
 
外需环境持续改善 
 
• 
一季度外需形势持续改善：高波动不改外需修复趋势。如果从月度出口表
现来看，一季度出口呈现出快上快下的高波动特征。但正如我们在
《20240413：出口读数回落背后需考虑扰动因素》所言，一季度的季节性
因素和基数落差主导了出口高波动。如果我们从整个季度的表现来看，
2024 年一季度出口无论是在当季同比，还是剔除基数影响后的两年复合同
比上，均呈现出上涨回升趋势。从这一角度来看，月度出口高波动不改现
阶段外需修复的趋势。 
• 
全球新一轮外需修复的另一信号：中间品贸易在复苏。从中间品在中国总
出口中的份额变化情况来看，其占比在2022 年下半年开始整体呈现逐步回
落趋势，事实上此节点也是中国新一轮外需回落周期开始的节点。但2024
年一季度，中国出口中的中间品份额显著抬升。结合开年以来全球主要电
子中间品出口国（越南、韩国）的出口增长、以及中国电子链条出口的见
底回升（详见《20240413：出口读数回落背后需考虑扰动因素》），全球新
一轮电子周期启动也为外需修复提升了重要助力。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 10 - 
图表6：从出口产品端来看，2024Q1 中国出口的主要拉动来自于交运设备、电子、家电和部分资本品 
 
数据来源：中国海关总署，兴业证券经济与金融研究院整理 
 
图表7：一季度中国对各经济体出口增速普遍回升 
 
 
 
注：为展示效果，此处并未给出对俄罗斯的季度出口同比.受高基数影响，其趋势为2024Q1 回落。 
数据来源：同花顺，兴业证券经济与金融研究院整理。 
 
• 
后续外需线索一：海外库存周期切换对中国外需的支撑。2024 年全球制造
业景气指数开始呈现逐步回升趋势，或带动美欧等发达经济体的企业补库
意愿修复。根据美国三大厂商的库存同比增速变化，2024 年其名义增速开
始见底回升，剔除生产价格后的实际库存增速也在2023 年四季度以来震荡
上行。结合2 月份库销比出现回落的边际变化，或指向本轮库存增速上行
更多源自于企业主动补库选择而非销售回落下的被动补库。历史经验来
看，海外补库周期启动对中国外需有积极推动（详见《20240106
库存的三条线索》）。而从产品端来看，当前美国制造商的交运设备、金属
制品、纺织轻工和能源品的库存增速已呈现上行趋势，计算机电子品仍整
体企稳。后续来看，全球新一轮库存周期的切换将为中国外需带来重要支
撑，相关商品的补库需求也将带来外需结构性机会。 
2022Q1
2022Q2
2022Q3
2022Q4
2023Q1
2023Q2
2023Q3
2023Q4
2023全年
2024Q1
锂电池
0.47%
0.71%
0.84%
0.70%
0.89%
0.50%
0.18%
0.03%
0.38%
-0.30%
光伏
0.92%
0.81%
0.65%
0.15%
0.22%
0.09%
-0.35%
-0.32%
-0.10%
-0.56%
电工器材
0.41%
0.54%
0.71%
0.12%
0.36%
0.01%
-0.57%
-0.42%
-0.17%
-0.17%
新能源车
0.46%
0.06%
0.42%
0.60%
0.59%
0.78%
0.34%
0.26%
0.49%
0.25%
汽车及其零部件
0.41%
0.37%
0.68%
0.39%
0.66%
1.02%
0.63%
0.81%
0.85%
0.55%
船舶
0.00%
-0.06%
-0.01%
0.07%
0.03%
0.06%
0.21%
0.37%
0.17%
0.66%
工程机械
0.49%
0.25%
0.61%
0.15%
0.22%
0.42%
-0.14%
0.10%
0.15%
0.21%
钢铁及其制品
0.94%
1.42%
0.87%
-0.20%
0.87%
-0.93%
-1.20%
-0.55%
-0.50%
-0.52%
能源产品
0.28%
0.17%
1.08%
0.88%
0.75%
-0.13%
-0.43%
-0.47%
-0.09%
-0.46%
陶瓷玻璃石料
0.00%
0.12%
0.21%
0.17%
0.25%
-0.07%
-0.38%
-0.49%
-0.23%
-0.22%
加热照明装置
0.02%
0.04%
0.13%
-0.02%
0.09%
0.03%
-0.14%
-0.08%
-0.03%
-0.03%
发动发电装置
0.67%
0.22%
0.32%
-0.32%
-0.08%
0.04%
-0.29%
0.01%
-0.08%
0.20%
化工
1.90%
1.60%
1.11%
-0.42%
-0.51%
-1.40%
-1.20%
-0.38%
-0.89%
0.03%
手机
-0.25%
-0.20%
0.27%
-1.89%
-0.55%
-1.05%
-0.89%
0.46%
-0.52%
-0.61%
电脑
0.77%
-0.02%
-0.42%
-2.15%
-2.25%
-1.16%
-1.26%
-0.72%
-1.32%
0.38%
其他消费电子
-0.10%
0.01%
0.00%
-0.22%
0.00%
-0.10%
-0.08%
-0.01%
-0.05%
0.04%
电子元件
1.05%
0.84%
-0.50%
-0.93%
-0.91%
-1.31%
-0.67%
-0.58%
-0.86%
0.71%
家电
-0.17%
-0.27%
-0.44%
-0.60%
-0.15%
0.04%
0.14%
0.24%
0.08%
0.30%
家具玩具
0.34%
0.69%
-0.29%
-0.73%
-0.17%
-0.69%
-0.73%
-0.18%
-0.46%
0.25%
纺服类
纺织服装鞋革箱包
0.91%
1.72%
1.00%
-0.54%
-0.06%
-0.42%
-1.29%
-0.59%
-0.61%
-0.04%
医药
0.75%
-0.71%
-0.67%
-0.70%
-1.08%
-0.16%
-0.19%
-0.09%
-0.36%
0.02%
其他机电产品
0.50%
-0.27%
-0.02%
-1.68%
0.20%
0.10%
-1.60%
-1.04%
-0.69%
0.16%
其他高新技术产品
1.31%
0.97%
1.11%
0.56%
-0.02%
0.13%
-0.06%
0.03%
0.02%
0.19%
其他未分类产品
3.54%
3.83%
2.30%
-0.27%
-0.12%
-1.41%
-0.96%
0.25%
-0.54%
0.45%
中国出口，同比拉动
地产产业链
其他
出口类别
新能源产业链
交运设备
顺周期类
电子产业链
-30.0%
-20.0%
-10.0%
0.0%
10.0%
20.0%
总出口
美国
欧盟
东盟
日本
中国香港
韩国
中国台湾
澳大利亚
印度
英国
加拿大
新西兰
拉丁美洲
非洲
出口季度同比：主要经济体
2024Q1
2023Q4
2023Q3
2023Q2
2023Q1
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 11 - 
 
图表 8：美国一季度经济增速走“弱”的背后是进口增加，消费仍保持韧性 
 
 
 
数据来源：CEIC，兴业证券经济与金融研究院整理 
 
图表9：美国名义库存增速见底回升，实际库存增速震荡回升 
 
 
 
数据来源：CEIC，兴业证券经济与金融研究院整理 
 
图表10：美国制造商的交运设备、金属制品、纺织轻工和能源品库存增速上行 
 
 
 
数据来源：CEIC，兴业证券经济与金融研究院整理 
-3
-2
-1
0
1
2
3
4
5
6
23/03
23/06
23/09
23/12
24/03
美国实际GDP季环比增速拆分，百分点
消费
固定投资
库存
净出口
政府支出和投资
GDP
1.2
1.3
1.4
1.5
1.6
1.7
1.8
-20.0
-15.0
-10.0
-5.0
0.0
5.0
10.0
15.0
20.0
25.0
15/01
16/01
17/01
18/01
19/01
20/01
21/01
22/01
23/01
24/01
美国名义库存同比，%
美国实际库存同比，%
美国库销比，右轴
-20.0
-10.0
0.0
10.0
20.0
30.0
40.0
美国制造商库存分行业同比，%
非金属矿产
原生金属（PM）
金属加工制品
机械（MA）
计算机和电子产品（CE）
电气设备及其他设备
交通运输设备（TE）
家具及相关产品
食物产品（食物）
饮料和烟草（BT）
服装
皮革及相关制品
基础化学品（CH）
橡胶和塑料制品
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 12 - 
 
• 
后续外需线索二：新兴经济体“再工业化”需求带来的外需机会。凭借后
发优势，新兴经济体在增长速度和空间上均有较大潜力，而其推进经济发
展同步带动的“再工业化”需求也为中国相关资本品带来重要的出口机
会。事实上从2023 年下半年以来，一带一路经济体对中国的资本品需求显
著强于其他商品。而从一季度整体出口表现来看，除了交运设备保持高景
气外，工程机械、发动机发电机等资本品类也表现亮眼。同时从工程机械
出口来看，东盟、中东、拉美和非洲是主要的需求来源和增长支撑。而在
中国贸易动能切换继续演绎的背景下，新兴经济体的“再工业化”需求和
中国对这些经济体的经贸合作深化，将为中国外需带来重要支撑。 
 
图表11：新兴经济体是中国工程机械需求的主要拉动 
 
 
 
数据来源：中国海关总署，兴业证券经济与金融研究院整理 
 
图表12：2023 年下半年开始，一带一路对中国的资本品需求显著强于其他商品 
 
 
 
数据来源：中国海关总署，兴业证券经济与金融研究院整理 
-20.0%
0.0%
20.0%
40.0%
60.0%
18/3
18/9
19/3
19/9
20/3
20/9
21/3
21/9
22/3
22/9
23/3
23/9
24/3
中国出口同比拉动：工程机械，季度
东盟
非洲
中亚
欧盟
中国香港
印度
日本
韩国
拉丁美洲
中东
俄罗斯
中国台湾
英国
美国
其他经济体
-40.0%
-20.0%
0.0%
20.0%
40.0%
60.0%
80.0%
100.0%
18/03 18/09 19/03 19/09 20/03 20/09 21/03 21/09 22/03 22/09 23/03 23/09 24/03
中国出口同比增速：一带一路经济体，季度
中间品
初级制品
消费品
资本品
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 13 - 
 
图表13：综合出口回升速度来看，新优势产业和电子家电等制造业或更加受益 
 
 
 
注：出口依赖度指标计算公式为出口交货值/营业收入*100%。“2023-2021”是“2023 年依赖度减2021 年
依赖度” 
数据来源：同花顺，兴业证券经济与金融研究院整理 
-6.0
-5.0
-4.0
-3.0
-2.0
-1.0
0.0
1.0
2.0
3.0
医药制造
文体娱乐
家具制造
通信电子
电气机械
金属制品
木制品
纺织
皮革制鞋
橡塑制品
农副加工
化学制品
酒饮料茶
有色加工
仪器仪表
非金制品
食品制造
其他制造
印刷
服装
烟草制品
通用设备
黑色加工
化纤制造
燃料加工
纸制品
专用设备
汽车制造
运输设备
各行业出口依赖度变化：2023-2021，%
防疫需求驱动
高出口敏感型，更易受
益新一轮全球外需修复
中出口敏感型，
较易受益新一轮
全球外需修复
新优势产业链，出
口竞争力稳步提升
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 14 - 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
外乱：全球地缘风险下的供需变化 
整体来看，当前我们可能并不处在一个所谓典型的“朱格拉周期”，即需求大幅扩
张或技术革新带来的投资周期。而供给端的因素，尤其是资源供给方面的供给
“割裂”一方面增加了供给端的不确定性，另一方面又反过来推升全球对于战略
重要部门的投资增长。
 
 
 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 15 - 
 
全球来看，地缘冲突持续处于高位 
 
• 
过去几年，全球地缘冲突持续处于高位。在地缘风险上升的初期，我们已
开始关注地缘风险对于全球商品供求方面的影响（
2022
4 月《商品
与美元：两只灰犀牛》）。我们当时的一些判断（全球去美元化的压力在上
升、商品价格上升且粮食、能源等商品可能成为地缘政治博弈中的筹码）
在过去几年正在演绎。与此同时，我们也观察到一些新的变化。 
 
图表 14：全球地缘冲突不断 
 
 
 
数据来源：Our World in Data，兴业证券经济与金融研究院整理 
 
地缘冲突的直接影响是相关工业需求增长 
• 
全球地缘政治冲突不断，直接影响是各个经济体军费开支的扩张。我们观
察到美国国防与航天工业设备生产指数（实际值）已创历史新高，前两个
高点分别是80 年代末冷战尾声以及2012 年本拉登毙命前后。除了美国以
外，北约国家军费支出快速扩张，根据北约组织3 月的报告估算2023 年北
约欧洲及加拿大实际军费支出同比增长约10%左右，其中设备支出增速达
到25%，这带动了相关产业的扩张，也推升了对相关原材料的需求。 
 
图表 15：美国国防与航天工业设备生产指数已创历史新高 
 
 
 
数据来源：CEIC，兴业证券经济与金融研究院整理 
0.0
50.0
100.0
150.0
200.0
89
92
95
98
01
04
07
10
13
16
19
22
全球武装冲突数量，个
非洲
美洲
亚太
欧洲
中东
0.0
20.0
40.0
60.0
80.0
100.0
120.0
140.0
47 50 53 56 59 62 65 68 71 74 77 80 83 86 89 92 95 98 01 04 07 10 13 16 19 22
美国国防及航天工业设备生产指数，季调
东欧剧变开始
911
俄乌冲突
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 16 - 
 
图表 16：北约军费快速增长 
 
 
 
注1：上述数据2017 年开始加入黑山，2020 年开始加入北马其顿，2023 年加入芬兰； 
注2：2023 年数据，如果2022 年也包含芬兰，实际军费支出同比增速为9.3%，仍远高于过去几年； 
注3：2023 年为北约在2024 年4 月5 日报告中的预测值。 
数据来源：North Atlantic Treaty Organization，兴业证券经济与金融研究院整理 
 
间接影响是加剧大宗供给割裂，反过来刺激投资需求 
• 
全球大宗商品产地集中、供需弹性弱，高度依赖贸易。大宗商品生产首先
依赖于资源禀赋，而全球资源的地理分布并不均衡，呈现大宗商品产地高
度集中的现状，而非产地国家必须进口大宗商品。其中，钴、锂等新能源
金属的产地集中度尤其高，也就是说全球产业链重构的“宠儿”——新能
源部门，其供给端脆弱性较大。除了产地集中，需求和供给弹性偏低也是
大宗商品的脆弱性来源，例如金属开采周期时间长、家庭对能源和农产品
的消费需求刚性。 
 
图表 17：全球资源禀赋不均衡，大宗商品产地集中度高，尤其是新能源金属 
 
 
 
注：受限于数据可得性，图中数据为2019 年数据 
数据来源：IMF，兴业证券经济与金融研究院整理 
 
• 
地缘割裂或加剧大宗价格对供给冲击的敏感度，推升全球通胀中枢。2018
年以来，对全球大宗商品部门的贸易干预数量持续上升，俄乌冲突后又进
一步加剧。过去，全球市场一体化提供了低廉的大宗商品，而随着自由贸
易程度下降，未来大宗商品贸易或向地缘同盟内部倾斜和集中，这可能带
来以下问题：一是同盟内部供给无法充分满足需求，例如美欧经济体所需
的精炼矿物矿石多由俄罗斯和南非等国生产，这将导致同盟内的稀缺资源
-2.7
-1.3
-0.9
1.6
3
5.9
4.3
3.6
4.7
2.6
3.8
11
-2.6
-0.6
-2.9
2.7
3.7
12.8
10.2
8.4
9.1
13.9
5.8
25.4
-5.0
0.0
5.0
10.0
15.0
20.0
25.0
30.0
2012
2013
2014
2015
2016
2017
2018
2019
2020
2021
2022
2023e
北约军费支出增长
北约欧洲及加拿大，实际军费支出，同比增速，%
其中：实际主要设备支出，同比增速，%
0
20
40
60
80
100
锂
钴
镍
铜
原油
小麦
精炼矿物矿石
开采矿物矿石
能源
农产品
不同大宗商品前三大产地国在全球总产量的占比，2019年，%
第一大
第二大
第三大
金属
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 17 - 
品价格上涨；二是如果同盟内部发生供给冲击，价格上升的弹性将更明显
——因为短期内缺少可替代的供给。在该背景下，全球通胀中枢或将长期
维持较高水平。 
• 
商品脆弱性或取决于产地国在不同地缘阵营间的分配。未来，除了供给和
需求弹性的基本因素，跨同盟资源分配格局也将是影响大宗商品价格的重
要因素，如果某一商品的主要产地国向特定阵营倾斜，则将造成另一方内
部价格上升。 
 
图表 18：对大宗商品的贸易干预数量持续增加，俄乌冲突后进一步加剧 
 
 
 
数据来源：IMF，兴业证券经济与金融研究院整理 
 
图表 19：地缘风险持续演绎，对大宗商品供给“割裂”的担忧明显升温 
 
 
 
数据来源：IMF，兴业证券经济与金融研究院整理 
 
• 
上述对于供应链的担忧反过来刺激了全球投资的增长，且集中在战略意义
较高的行业。全球商品供给的“割裂”带来的另一个影响是反过来刺激各
个经济体对于产业链的投资增长。正如我们在此前报告中所指出的，2020
年之后我们观察到全球产业链正在发生一些变化。而本轮全球产业链重构
的逻辑与上一轮不同。冷战结束后的前三十多年，全球化程度大幅提高，
其核心推动力是市场主体“效率优先”的诉求。而本轮全球产业链重构
中，“抗风险能力”明显占据更重要的位置（具体参见《何必悲观-全球产
业链重构的中国视角》）。因而，我们看到本轮产业链重构集中在部分战略
意义较高的行业——半导体、新能源，且对于发达经济体政府补贴或贸易
壁垒的要求较高。而传统制造业由于安全重要性排序在上述几个行业之
后，因而在本轮产业链重构中的转移并不明显。 
0
100
200
300
400
500
600
700
2009 2010 2011 2012 2013 2014 2015 2016 2017 2018 2019 2020 2021 2022
全球贸易干预数量，2016-19=100
农产品
能源
矿石矿物
所有商品
0
50
100
150
200
250
300
0
250
500
750
1,000
1,250
1,500
2013
2014
2015
2016
2017
2018
2019
2020
2021
2022
2023
财报电话会“割裂”关键词指数，全部部门，2013-2015=100
财报电话会“割裂”关键词指数，大宗商品部门，2013-2015=100
地缘风险指数，2013-2015=100，右轴
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 18 - 
 
图表 20：2023 年全球投资占GDP 比重以及跨境绿地投资继续处于高位 
 
 
 
数据来源：CEIC，UNCTAD，兴业证券经济与金融研究院整理 
 
图表 21：2023 年的全球绿地投资依然集中在战略重要性的行业 
 
 
 
数据来源：The 2023 investment matrix，fdiintelligence，兴业证券经济与金融研究院整理 
 
• 
资源等“硬资产”的重要性上升又进一步推动资源型新兴经济体谋发展的
诉求上升。一方面，全球新能源“投资热”使得资源获取的诉求再次上
升，过去几年资源的开采量增速明显回升，尤其是矿物资源；另一方面，
资源国在大国博弈中的议价能力上升（参见《本币结算风潮》），使得部分
新兴经济体（以中东、中亚、非洲为主）工业化的诉求开始明显上升，我
们看到，如沙特等资源类经济体均在经济发展规划中提出工业化的目标，
具体而言包括完善基建、提高新能源产业能力、以及部分其他制造业的生
产能力（如中东选择汽车、电子；非洲选择新能源及数据中心等）几个方
向。从数据来看，多个资源型经济体的资本形成（或其中设备投资）占
GDP 的比重明显回升，而这又会从反过来推升相关上游原材料的需求增
长。 
22
23
24
25
26
27
28
0
200
400
600
800
1,000
1,200
1,400
80
83
86
89
92
95
98
01
04
07
10
13
16
19
22
全球外商直接投资，绿地投资，十亿美元
全球投资/GDP，右轴
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 19 - 
 
图表 22：全球资源获取诉求再次上升 
 
 
 
数据来源：Global Material Flows Database，兴业证券经济与金融研究院整理 
 
图表 23：资源型经济体资本形成占GDP 的比重 
全球部分资源品出口经济体资本形成（或其中设备投资）占GDP 比重，实际值，% 
 
 
2010 
2011 
2012 
2013 
2014 
2015 
2016 
2017 
2018 
2019 
2020 
2021 
2022 
2023 
澳大利亚 
资本形成:设备 
4 
5 
5 
4 
4 
4 
3 
3 
4 
4 
3 
4 
4 
4 
俄罗斯 
资本形成 
 
21 
21 
21 
21 
19 
19 
20 
19 
19 
19 
19 
21 
22 
巴西 
资本形成 
22 
22 
22 
23 
22 
19 
18 
17 
17 
18 
18 
20 
19 
18 
印尼 
资本形成:设备 
3 
4 
4 
4 
4 
3 
3 
3 
4 
4 
3 
3 
4 
4 
沙特 
资本形成 
22 
23 
23 
24 
25 
24 
21 
21 
21 
21 
20 
21 
24 
25 
南非 
资本形成:设备 
5 
5 
5 
6 
5 
5 
5 
5 
5 
5 
5 
5 
5 
6 
哈萨克斯坦 
资本形成 
24 
21 
23 
22 
22 
23 
23 
22 
21 
23 
25 
23 
22 
26 
 
注1：根据Global Resource Outlook,2024 的报告，2020 年前十大资源净出口国为澳大利亚、俄罗斯、巴西、印尼、加拿大、沙特、南非、伊拉克、
哈萨克斯坦、UAE，由于伊拉克、UAE 缺少资本形成相关数据； 
注2：哈萨克斯坦由于缺少实际数据，为名义值。 
数据来源：CEIC，兴业证券经济与金融研究院整理 
 
• 
整体来看，当前我们可能并不处在一个所谓典型的“朱格拉周期”，即需求
大幅扩张或技术革新带来的投资周期。而是供给端的因素，尤其是资源供
给方面的供给“割裂”一方面增加了供给端的不确定性，另一方面又反过
来推升全球对于战略重要部门的投资增长以及对于资源的获取。资源型经
济体在当前话语权上升的背景下，自身工业化的诉求也在上升，这又反过
来提升了原材料的需求预期。 
0.0%
1.0%
2.0%
3.0%
4.0%
5.0%
 1971~1980
 1981~1990
 1991~2000
 2001~2010
 2011~2020
 2021~2023
全球开采量年化增速
生物质能
化石燃料
金属矿物
非金属矿物
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 20 - 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
“外乱内稳”下的大类资产配置 
短期看，中国经济内需企稳，外需持续改善，政策呵护仍有空间；中期看，全球
地缘紧张局势延续焦灼态势；“外乱内稳”环境下，海外资金有流入中国市场的空
间。结构上来看，需求有张力和地缘形势升级将从供求两端一起继续拉升通胀，
尤其是资源品和原材料的价格，这可能也将成为二季度及后续影响资产配置的一
条重要线索。 
 
 
 
 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 21 - 
 
权益资产：不仅有估值优势，还有政策呵护和助力 
 
• 
“外乱内稳”下，北上资金呈现流入。短期看，中国经济内需企稳，外需
持续改善，政策呵护仍有空间；中期看，全球地缘紧张局势延续焦灼态
势；“外乱内稳”环境下，海外资金有流入中国市场的空间，4 月底以来已
在逐渐落地。 
 
• 
从资产配置格局演变和估值比较的角度来看，权益资产配置价值上升。当
前中国经济结构转型向纵深推进，地产部门放缓已逐步体现，房地产市场
投资价值回落，长期配置型资金流入地产市场的动力明显下降。对于债券
市场而言，经济增速下行以及政策持续“促进综合融资成本稳中有降”，意
味着从战术配置角度债券资产持续存在资本利得，但从战略配置角度而
言，利率债收益率已大幅回落且交易拥挤，利率债配置性价比已在下降；
而在“一揽子化债”不断推进过程中，部分高收益信用债可能也面临缩
量，信用债市场对长期配置资金的吸纳能力也在下降。无论是从中长期经
济深化转型背景下资产配置格局的演变趋势看，还是从短期资金对地产、
债券和权益等资产的风险偏好以及估值性价比来看，权益资产的配置价值
正在上升。 
 
图表24：从股债对比角度看，权益资产的相对性价比在上升 
 
 
 
数据来源：Wind，同花顺，兴业证券经济与金融研究院整理 
 
• 
政策高度重视资本市场，发力部署资本市场制度改革和稳定性提升。2023
年7 月政治局会议提出“要活跃资本市场，提振投资者信心”。2023 年四季
度中央金融工作会议提出“切实加强对重大战略、重点领域和薄弱环节的
优质金融服务……更好发挥资本市场枢纽功能”。2024 年1 月习总书记在省
部级主要领导干部推动金融高质量发展专题研讨班开班式上发表重要讲话
时指出，“坚持经济和金融一盘棋思想”。2024 年1 月国务院常务会议及3
月政府工作报告指出，要“增强市场内在稳定性”，4 月新“国九条”细化
部署加强对于上市公司准入、在市、退市各阶段的监管，大力推进资本市
场制度完善改革。整体来看，后续随着政策部署逐渐落地推进，我国资本
市场制度体系将不断完善、内在稳定性将获得提升，权益市场此前的波动
格局或将改变。随着波动率下降，权益市场的性价比相对其他资产将提
升，对长期配置资金的吸引力或将明显上升。 
-4
-3
-2
-1
0
1
2
3
4
5
6
05
06
07
08
09
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
万得全A E/P - 10年期国债收益率，%
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 22 - 
图表 25：近期资本市场相关政策部署情况 
时间 
会议/部门 
资本市场相关政策部署情况 
2023/7/24 
政治局会议 
要活跃资本市场，提振投资者信心。 
2023/8/27 
财政部 税务总局 
证券交易印花税实施减半征收 
2023/8/27 
证监会 
阶段性收紧IPO 节奏，进一步规范股份减持行为 
2023/8/27 
交易所 
降低融资保证金比例 
2023/10/30 
财政部 
引导保险资金长期稳健投资，加强国有商业保险公司长周期考核。 
2023/10/31 
中央金融工作会议 
要切实加强对重大战略、重点领域和薄弱环节的优质金融服务……优化融资结构，更好发挥资本市场枢纽功
能，推动股票发行注册制走深走实，发展多元化股权融资，大力提高上市公司质量，培育一流投资银行和投资
机构……活跃资本市场 
2023/11/3 
证监会 
引导公募基金行业将更多资金配置到战略新兴产业等国家最需要的地方，提高公募基金在A 股市场的持股比例 
2024/1/22 
国常会 
要进一步健全完善资本市场基础制度，更加注重投融资动态平衡，大力提升上市公司质量和投资价值，加大中
长期资金入市力度，增强市场内在稳定性。要加强资本市场监管，对违法违规行为“零容忍”，打造规范透明的
市场环境。要采取更加有力有效措施，着力稳市场、稳信心。要增强宏观政策取向一致性，加强政策工具创新
和协调配合，巩固和增强经济回升向好态势，促进资本市场平稳健康发展。 
2024/1/24 
国资委 
进一步研究将市值管理纳入中央企业负责人业绩考核。……及时通过应用市场化增持、回购等手段传递信心、
稳定预期，加大现金分红力度，更好地回报投资者。 
2024/1/24 
证监会 
建设以投资者为本的资本市场：让广大投资者有回报、有获得感。一是大力提升上市公司质量；二是回报投资
者要发挥证券基金机构的作用；三是梳理完善基础制度安排。 
2024/1/28 
证监会 
进一步加强融券业务监管，全面暂停限售股出借 
2024/3/5 
《政府工作报告》 增强资本市场内在稳定性。 
2024/4/12 
国务院 
《发布“国九条”》。一、总体要求。二、严把发行上市准入关。三、严格上市公司持续监管。四、加大退市监管
力度。五、加强证券基金机构监管，推动行业回归本源、做优做强。六、加强交易监管，增强资本市场内在稳
定性。七、大力推动中长期资金入市，持续壮大长期投资力量。八、进一步全面深化改革开放，更好服务高质
量发展。九、推动形成促进资本市场高质量发展的合力 
2024/4/12 
证监会 
发行监管方面，包括2 项规则修订。一是修订《科创属性评价指引（试行）》,二是修订《中国证监会随机抽查
事项清单》。上市公司监管方面，包括1 项规则制定、1 项规则修订。一是制定《上市公司股东减持股份管理办
法》,二是修订《上市公司董事、监事和高级管理人员所持本公司股份及其变动管理规则》。证券公司监管方
面，主要是修订《关于加强上市证券公司监管的规定》，旨在通过加强监管，发挥上市证券公司推动行业高质-
量发展的引领示范作用。交易监管方面，制定《证券市场程序化交易管理规定（试行）》。 
2024/4/12 
证监会 
《退市意见》具体包括以下几个方面，第一，严格强制退市标准。一是严格重大违法退市适用范围，调低2 年
财务造假触发重大违法退市的门槛，新增1 年严重造假、多年连续造假退市情形。二是将资金占用长期不解决
导致资产被“掏空”、多年连续内控非标意见、控制权无序争夺导致投资者无法获取上市公司有效信息等纳入规
范类退市情形，增强规范运作强约束。三是提高亏损公司的营业收入退市指标，加大绩差公司退市力度。四是
完善市值标准等交易类退市指标。第二，进一步畅通多元退市渠道。第三，削减“壳”资源价值。第四，强化退
市监管。第五，落实退市投资者赔偿救济。 
 
数据来源：中国政府网，财政部，证监会，国资委，上海交易所，深圳交易所，兴业证券经济与金融研究院整理 
 
• 
从“外乱内稳”角度寻找权益资产配置线索：制造优势、需求出海、上游
资源。 
 
全球政经冲突和地缘局势升级线索下的中国制造优势。从全球制造业
格局演变趋势看，虽然近年来全球产业链割裂不断演绎，但是中国拥
有完备的产业体系，在全球制造业中有优势、占比也有安全边际，这
是中国制造优势的体现。从权益资产定价看，2023 年以来，A 股权益
资产对中国制造优势的定价有明显低估，后续有修复空间。 
 
中国优势制造业的对外输出——外需拉动和产业出海。从中国出口在
全球的占比看，疫情之后一直保持较好韧性。随着中国制造在全球优
势的体现，外需拉动的行业和优势产业出海扩张，仍然是值得持续关
注的行业赛道。 
 
通胀环境下资源品、原材料涨价线索下的上游资源。中东、俄乌地缘
局势在美国的介入下焦灼态势短期难以改善，海外需求韧性和中国经
济企稳背景下全球需求端也有张力，供求两端因素将一起继续张拉通
胀。在此背景下，资源品、原材料涨价是权益资产配置的一条关键线
索，在大宗商品已经有所反映后，股市上游资源板块可以关注。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 23 - 
 
图表 26：2023 年以来，A 股权益资产对中国制造优势的定价有明显低估 
 
 
 
数据来源：Wind，CEIC，兴业证券经济与金融研究院整理 
 
商品：制造业周期+地缘不确定+通胀的长逻辑支撑下
进入新中枢 
 
• 
2024 年以来，黄金和有色金属为代表的大宗商品涨幅较大。今年以来大宗
商品的上涨主要受到三重因素的推动：第一，一季度美债收益率回落叠加
全球PMI 回暖，制造业周期启动预期下大宗商品需求上行；第二，地缘波
动加剧，避险情绪推动黄金价格上涨；第三，通胀韧性超预期，抗通胀情
绪下对大宗商品投资的偏好。长逻辑支撑下，大宗商品呈现中枢上行的趋
势。 
• 
然而，大宗商品表现也有分化，今年有色整体好于黑色。今年前三个月，
有色和黑色表现呈现明显分化——有色震荡上行而黑色下跌，直至4 月起
二者同涨。然而再次向前追溯，有色与黑色的分化其实从2023 年8 月便开
始了，彼时有色随着紧缩预期的升温而明显回落，而黑色由于中国经济预
期的改善和供给的扰动，呈现上涨。因此，今年年初有色和黑色的分化一
定程度上是此前市场过度反应的回调，而4 月以来二者再次同步上涨受到
了上文所述的长逻辑的催化。 
 
图表 27：2024 年以来，商品表现有所分化，有色和贵金属涨幅较大 
 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
12.0%
12.5%
13.0%
13.5%
14.0%
14.5%
15.0%
15.5%
16.0%
4,000
5,000
6,000
7,000
8,000
9,000
10,000
11,000
12,000
13,000
14,000
14
17
20
23
中证股票基金指数
中国出口份额，12MMA，中心移动平均，右轴
-15.0
-10.0
-5.0
0.0
5.0
10.0
15.0
20.0
25.0
Wind商品指数涨跌幅，2024/1/2-2024/4/25，%
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 24 - 
 
图表 28：大宗有色和黑色从2023 年8 月以来走背，2024 年4 月再次同步 
 
 
 
注：有色指数包含沪铜、沪铝、沪锌、沪铅、沪镍、沪锡；黑色指数包含铁矿石、焦炭、焦煤、硅铁、
螺纹钢、线材、热轧卷板、锰硅。 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
• 
黄金：今年以来的涨幅主要由于交易情绪面等非宏观因素的支撑。在黄金
价格的传统模型中，通胀预期、实际利率、美元、央行放水等因素通常能
够解释一般情景下的黄金涨跌。然而，今年以来黄金涨幅较大，而这些传
统的宏观因素的贡献非但不能解释其中的部分涨幅，反而呈现负向拖累。
因此，今年以来黄金的上涨或已经一定程度上脱离了传统的宏观基本面因
素。正如我们在报告《谁在买黄金？》中所分析的，当前黄金需求升温的
边际推手主要来自于OTC，而其背后还是地缘的折射和避险需求。 
 
图表 29：2024 年金价的上涨主要是由于非宏观基本面因素贡献的 
 
 
 
数据来源：Wind，Bloomberg，Caldara, Dario, and Matteo Iacoviello (2021),兴业证券经济与金融研究院整理 
 
• 
铜：全球制造业周期启动背景下，铜价或已进入新中枢。2023 年以来，铜
价已经脱离了原本的经济增长框架，呈现出了超额上行。究其原因，2023
年美国高端制造业回流政策下，计算机、电子电器厂房的建造支出快速上
升，拉动了铜的需求。2024 年，全球PMI 呈现回暖趋势，美国或将进入设
备投资阶段，而中国“设备更新”政策下，铜的需求或有持续支撑。 
400
500
600
700
800
900
1,000
1,300.0
1,500.0
1,700.0
1,900.0
2,100.0
2,300.0
2,500.0
22-01
22-04
22-07
22-10
23-01
23-04
23-07
23-10
24-01
24-04
Wind大宗商品指数
有色
黑色，右轴
-30.0
-20.0
-10.0
0.0
10.0
20.0
30.0
40.0
50.0
07
08
09
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
黄金价格涨跌幅归因，%
通胀预期
美元
实际利率
地缘风险
FED总资产
油价
其他
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 25 - 
 
图表 30：2023 年以来，铜价或已脱离原本的经济框架，进入新轨道 
 
 
 
数据来源：Wind，CEIC，兴业证券经济与金融研究院整理 
 
债券资产：拥挤交易下出现波动，但长期逻辑不变 
 
• 
近期债市出现拥挤交易下的波动风险。近期央行多次表态，需关注利率波
动风险。4 月23 日，央行在接受《金融时报》采访时再次表示“当前长期
国债收益率持续下滑的底层逻辑是市场上‘安全资产’的缺失，随着未来
超长期特别国债的发行，“资产荒”的情况会有缓解，长期国债收益率也将
出现回升……固定利率的长期限债券久期长，对利率波动比较敏感，投资
者需要高度重视利率风险”。因而，尽管长期我们依然看好中国债市，但短
期考虑到性价比等因素我们将债券资产的优先序置于权益及商品之后。 
• 
但债券市场的长期逻辑均未变化。我们在2024 年年度策略《修复信心：切
换、恢复、再平衡》中指出经济的结构性调整持续、存量债务问题化解、
全社会信用派生模式变化、住户部门行为模式切换几大逻辑支撑中国债券
市场的长期逻辑。当前来看，这些逻辑均未发生变化。结合此前我们对日
本90 年代股债市场复盘（
90 年代日本股债市场复盘》），在内生增长
动能明显加强且存量债务问题化解结束之前，债券收益率下行趋势较难逆
转。 
 
 
 
1986 1987 
1988 
1989 
1990 
1991 
1992 
1993 
1994 
1995 
1996 
1997 
1998 
1999 
2000 
2001 
2002 
2003 
2007 
2008 
2009 
2010 
2011 
2012 
2013 
2014 
2015 
2016 
2017 
2018 
2019 
2020 
2021 
2022 
2023 
2024 
1,000
2,000
3,000
4,000
5,000
6,000
7,000
8,000
9,000
10,000
11,000
-5.0
-3.0
-1.0
1.0
3.0
5.0
7.0
9.0
LME
（中国+美国）名义增速-美国10Y国债收益率，%
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 26 - 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
资产配置建议的量化方案 
结合各大类资产的定性分析，我们将用定量模型最终实现各类资产的配
置权重。本部分详细介绍资产配置模型的目标设定和投资约束、介绍资
产配置模型的战略配置组合以及战术资产配置模型的生成方法，最终给
出战术资产配置建议。 
 
 
 
 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 27 - 
 
政策设定与资产划分 
• 
我们认为完整的资产配置流程包括以下四个方面，即：政策设定、资产划
分、战略资产配置和战术资产配置，其中政策设定和资产划分是为后续战
略和战术配置模型的设计和执行提供行动指南，是进行组合配置建模的前
提条件。在多数组合配置方案中，资产配置的政策设定和划分多数被忽
视、或表述不够完善，这对于方案的贯彻执行有负面影响。因此，我们尝
试将资产配置方案设计更明确的表述出来，给投资者更全面完善的参考。 
• 
本节将详细对我们资产配置策略的投资目标、投资约束和资产选择进行介
绍。 
 
图表31：资产配置流程示意 
 
 
 
数据来源：兴业证券经济与金融研究院整理 
 
投资目标 
• 
立足于长期投资、多元分散化投资理念，我们尝试针对不同风险偏好投资
者构建保守、稳健和积极三种风险等级的配置组合，三类组合对应的波动
率目标为5%,10%和12%，对应在极端情形下的回撤控制在10%, 20%和
30%。为实现长期投资复合收益最大化的目标，组合并不进行被动的止损
管理或回撤控制而更强调主动事前的风险管理。 
• 
由于不同经济阶段风险资产的收益能力存在显著差异，因此组合在不同阶
段的预期收益也会出现波动，因此在投资目标层面更多从风险角度进行管
理，而在组合配置建模阶段结合大类资产的预期收益给出相应的组合预期
收益目标。 
投资约束 
• 
考虑到大类资产在不同时期在长期和短期的预期收益存在较大区别，因此
我们并不对大类资产的持仓权重进行主观约束，而更强调从组合波动风险
角度进行管理，这里既包括上述投资目标中组合波动率的约束，也包括战
术组合动态偏离幅度的约束。 
• 
在战术组合中，我们给定保守、稳健和积极组合相对战略参考组合的跟踪
误差控制在1%,3%和5%范围内，除跟踪误差约束之外，为了降低组合换
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 28 - 
手和提高稳定性，我们将适度对战术组合的权重偏离幅度进行控制约束。 
资产选择 
• 
考虑到国内多数机构投资者对于投资海外资产和一级市场产品存在或多或
少的政策限制，因此我们将资产配置的投资工具约束在国内二级市场范围
之内，包括权益、债券、商品期货、实物商品和现金管理工具等大类资
产。 
• 
在此基础上，我们尝试使用两层的资产类别划分架构，在划分第一层国内
大类资产类别基础上，进一步给出了细分资产的配置选择，具体来说主要
针对权益、债券和商品期货三类资产设置了相对应的细分资产，其中权益
资产中包括大中小盘，债券包括长期利率债和信用债，商品期货则包括了
工业品和农产品。我们强调通过细分资产的战略战术配置来进一步提高组
合的收益和风险控制能力1。  
 
战略资产配置组合 
• 
战略资产配置的主要任务是基于对大类资产长期收益风险的合理估计，结
合组合配置模型给出参考组合，作为战术配置模型的参考，但考虑到国内
大类资产的波动幅度较大，因此即使长期的预期收益也可能在年内出现明
显变化。因此，我们依然会季度对大类资产的预期收益进行更新，并计算
相应的组合配置权重，为平衡战略组合的稳定性和及时性，我们会对战略
资产配置的参考组合进行不定期的调整。 
• 
本节将重点介绍我们对大类资产长期预期收益的建模分析框架，并基于此
给出战略资产配置的参考组合。 
 
大类资产长期收益风险预测 
• 
考虑到资产划分阶段我们将大类资产划分为一级资产和细分资产两个级
别，在本文的分析中我们将尝试直接对细分资产的预期收益进行建模，并
汇总至一级资产给出其预期收益，并最终给出一级资产的战略配置建议
2。 
• 
下表给出了不同大类资产长期预期收益的分析逻辑框架，包括影响大类资
产长期收益的决定性因素，以及相应的动态调整项目。我们基于历史数据
将决定性因素和资产滚动收益率进行分解或回归建模，并基于当前环境下
的宏观状态预判，给出各资产长期收益的估计。 
 
1  具体对应Wind 代码：N00300.CSI, N00905.CSI, H00852.SH, CBA00651.CS, 
CBA02701.CS, NH0200.NHF, NH0300.NHF, AU9999.SGE, H11025.CSI 
2 在划分资产级别之后，战略资产配置也包括一级资产的配置和细分资产的配置两个
层面，考虑到细分资产的两两相关性较高，因此在一般条件下，我们默认将等权作
为细分资产的配置基准，因而可以针对细分资产进行预期收益建模，并推导得出一
级资产的预期收益。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 29 - 
 
图表32：风险资产长期预期收益分析框架 
 
资产类别 
长期决定性因素 
权益 
使用收益分解法预测股票资产未来长期收益。 
债券 
直接决定性因素为债券当前到期收益率水平，到期收益率取决于经
济增速、通胀预期。 
商品期货 
工业品的决定性因素为PPI 增速，农产品决定性因素为CPI 增速 
黄金 
上海金的决定性因素为美国实际利率和人民币汇率。 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
• 
对于权益类资产，我们使用收益分解法预测股票资产未来长期收益。股票
收益可以分解为股息、EPS 增长和PE 估值水平变动： 
(1
)
(1
)
1
EPS
PE
R
d
g
g
=
+
+
×
+
− 
其中R 表示未来t 期的年化股票总收益；d 表示未来t 期的平均股息率；
EPS
g
表示未来t 期每股净收益的年化增长率；
PE
g
表示PE 估值水平在未来
t 期的年化平均变动率。我们用当前股息率作为未来长期的股息率预测值；
假设PE 估值水平在未来10 年回复至过去10 年均值；并假设未来长期EPS
增速等于未来名义GDP 增速减去稀释效应。我们对中国未来5 年的经济实
际增速和CPI 增速预测结果计算名义经济增速预测值，假设全市场股票的
平均EPS 稀释效应大小为1%，即市场总体EPS 增速比经济增速慢1%左
右。在进行测算时，以Wind 全A 指数代表股票市场总体，则未来5年预期
股息率为1.4708%，PE 年化变动率为-2.1523%，名义GDP 年化增速为
8.5421%，通过上述公式可得权益资产整体未来5 年的预期收益为年化
0.063135。如果以股票基金为配置标的，还需要考虑主动管理带来的
Alpha。根据2005 至2020 年的数据，普通股票型基金指数相对Wind 全A
指数有年化0.04368 的超额收益，因此股票基金资产未来5 年的预期年化收
益为10.68%。 
• 
对于债券、大宗商品期货我们也尝试使用回归模型对资产收益变化进行解
释和预测，以工业品商品期货为例，我们将PPI 年度同比增速作为解释变
量，对工业品商品期货的当年收益进行回归分析，可以看到解释变量的T
值超过3，回归模型R2 达到50%，因此我们可以结合对未来中长期PPI 增
速预判给出预期收益值。 
 
图表 33：南华工业品商品期货收益分析 
 
类别 
回归系数 
标准误差 
T 值 
P 值 
常数项 
0.00099  
0.02 
0.046  
96% 
PPI 年度增速 
3.357 
1.10 
3.044 
1.4% 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
• 
由于篇幅限制，我们将不逐一介绍各大类资产长期收益的建模过程，下表
展示了我们对各细分资产未来五年的年化复合收益预测结果，以及预测过
程中使用的核心假设情况。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 30 - 
 
图表 34：各类细分资产中长期收益率预测值（预测日20240430） 
 
资产类别 
预期收益 
核心假设 
权益 
3.62% 
使用收益分解法将股票收益进行拆分，并分项预测股票资产
未来长期收益； 
利率债 
1.14% 
分别使用十年期国债到期收益率和AA+企业债对未来五年复
合收益率进行回归预测建模，并基于当前数据给出预期值； 
信用债 
3.82% 
工业品期货 
-0.57% 
假设未来PPI 同比增速为-0.2% 
农产品期货 
2.3% 
依据对未来长期CPI 增速预期进行判断 
上海黄金 
9.16% 
预计未来美国实际利率为0.1%，美元兑人民币汇率保持稳定 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
• 
由于细分资产间相关性较高，因此暂时我们不对细分资产进行主动战略配
置，当前以经验性等权作为基准：即权益资产内部沪深300:中证500:中证
1000 的比例为1/3:1/3:1/3，债券资产内部利率:信用为50%:50%，商品期货
资产内部工业:农产品=2/3:1/3。基于细分资产的收益预测结果，结合细分
资产的内部权重设定，我们给出了大类资产的预期收益和风险情况。 
 
图表35：大类资产长期收益风险预测结果 
 
资产类别 
预期收益 
预期波动率 
相关系数矩阵 
权益 
11.22% 
(Beta7.5972%+Alpha3.
6215%) 
20.6% 
100.0% 
-10.5% 
23.9% 
8.9% 
债券 
2.94% (Beta 
2.48%+Alpha0.46%) 
2.3% 
-10.5% 
100.0% 
-15.4% 
2.0% 
商品 
期货 
0.40% 
14.5% 
23.9% 
-15.4% 
100.0% 
26.4% 
实物 
黄金 
9.16% 
14.0% 
8.9% 
2.0% 
26.4% 
100.0% 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
• 
值得说明的是，考虑到实际投资中细分资产的配置往往会同时包含市场
Beta 收益和主动Alpha 收益，尤其是针对权益和债券类资产，其中Beta 收
益基于预测模型给出，而Alpha 收益则需要结合当前市场实际情况来预
估。本文中将股票型基金指数相对中证全指的年化超额收益，以及纯债型
基金指数相对中债总财富指数的年化超额收益作为Alpha 的估计参考值，
汇总得到投资者对未来各大类资产进行投资获得的合理预期收益。 
• 
最后，考虑到资产波动率的延续性较强，我们基于各类资产长期的历史月
度收益率汇总计算了资产的历史长期波动率和相关系数矩阵，作为对未来
长期风险指标的预测。从波动风险来看，权益资产大于商品大于债券；从
相关系数矩阵来看，债券资产能够有效分散权益资产的下行风险，商品期
货能够有效分散债券资产的下行风险，而实物黄金则跟传统股债资产都保
持较低相关性。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 31 - 
 
战略配置参考组合 
• 
在对一级大类资产收益风险预测的基础上，我们结合重抽样均值方差模型
3给出了不同风险约束下，大类资产的建议配置比例。随着组合目标波动率
的提升，权益资产的配置比例逐步提升，债券资产的配置比例明显下降，
商品类资产中实物黄金的配置比例高于商品期货，主要在于黄金对权益资
产的分散化效果优于商品期货。 
 
图表36：不同风险目标下大类资产战略配置参考组合配置建议 
 
 
 
注：纵轴表示配置比例，横轴表示预期波动率。具体参见正文。 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
• 
具体来说，下表展示了不同目标波动率组合的大类资产配置权重，进一步
结合细分资产的配置结构，我们给出了细分资产的战略配置组合权重，这
将作为战术配置时的参考组合，也是作为战术配置模型的考核基准。 
• 
值得说明的是战略资产配置中未对现金类资产给予配置权重，主要原因是
当前无风险资产的预期收益较低，因此暂时只在战术配置中进行择机配
置。 
 
图表37：不同风险等级的大类资产战略配置参考组合 
 
组合类型 
权益 
债券 
商品期货 
实物黄金 
保守 
18.31% 
56.09% 
6.41% 
19.19% 
稳健 
41.08% 
15.93% 
8.98% 
34.01% 
积极 
52.00% 
6.00% 
6.00% 
36.00% 
 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
图表38：不同风险等级的细分资产战略配置参考组合 
组合类型 
沪深300 
中证500 
中证1000 
利率债 
信用债 
工业品期货 
农产品期货 
实物黄金 
保守 
6.1% 
6.1% 
6.1% 
28.0% 
28.0% 
4.3% 
2.1% 
19.2% 
稳健 
13.7% 
13.7% 
13.7% 
8.0% 
8.0% 
6.0% 
3.0% 
34.0% 
积极 
17.3% 
17.3% 
17.3% 
3.0% 
3.0% 
4.0% 
2.0% 
36.0% 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
3 2018Q1 报告中对模型构建方法进行了详细描述。 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 32 - 
 
• 
综合来说，战略配置的环节一方面是对各大类资产理性预期收益率的合理
估计，另一方面也是为形成合理的参考组合打下坚实的逻辑分析预判基
础。反过来，对于已经设定了战略配置基准的投资者，也可以反向检验当
前组合配置权重是否跟定性分析的结论能够吻合。 
 
战术资产配置组合 
短期资产风险收益预判 
• 
基于兴业金工团队大类资产季度风险预测的方法，我们得到对各类资产下
季度波动率的预测结果，如下表所示。可以看到当前大盘股的波动率低于
历史长期水平，模型预测值同样低于历史长期水平，而中盘股和小盘股波
动率高于长期波动率；利率债和信用债资产的当前波动率也低于历史长期
水平；商品期货当前波动率处于历史相对较低水平；实物黄金当前波动率
和模型预测值均低于历史波动率。 
 
图表39：各类资产未来季度波动率预测 
 
 
当期波动率 
预测波动率 
长期波动率 
预测能力 
解释R2 
沪深300 
15.98% 
18.21% 
25.55% 
☆☆☆ 
44.00% 
中证500 
30.93% 
29.23% 
29.03% 
☆☆☆ 
39.64% 
中证1000 
37.67% 
33.53% 
30.17% 
☆☆☆ 
33.27% 
利率债 
1.89% 
2.32% 
2.78% 
☆☆☆ 
57.54% 
信用债 
0.33% 
1.09% 
1.09% 
☆ 
16.22% 
工业品期货 
10.09% 
13.60% 
18.65% 
☆☆ 
27.37% 
农产品期货 
8.32% 
9.63% 
11.97% 
☆☆ 
25.32% 
实物黄金 
9.06% 
11.31% 
15.32% 
☆☆ 
26.36% 
 
 
注：星级越高代表预测能力越强，对应回归模型的R2  
其中，☆☆☆代表R2≥30%，☆☆代表30%≥R2≥10%，☆代表R2≤10% 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
最终战术资产配置组合 
• 
基于大类资产的风险预测，以及宏观团队对大类资产收益方向的判断，我
们尝试构建动态战术组合，具体组合构建方法如下：首先，在参考战略组
合的基础上，结合收益预判的方向观点，我们给予超配和低配资产进行适
当的权重偏离
4，构建了目标偏离组合；其次，构建组合优化模型，优化
目标为相对目标偏离组合的权重差异最小化，而在对模型中资产的总权重
和分类权重进行偏离约束，以及相对参考组合的跟踪误差进行偏离管理，
当前方案下我们针对保守、稳健和积极组合的要求跟踪误差需要控制在
1%, 3%和5%的范围之内；最后，基于组合优化模型给出最终的战术配置
权重。 
• 
下表中展示了最新针对保守、稳健和积极组合的资产配置建议结果。从战
术配置结果来看，相对战略参考组合，模型超配了大盘股、中盘股、农产
品、工业品和黄金。 
 
4 当前设置的单资产偏离度为其原权重的30% 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 33 - 
图表40：各资产配置建议 
组合类型 
沪深300 
中证500 
中证1000 
利率债 
信用债 
工业品期货 
农产品期货 
实物黄金 
保守 
7.4% 
8.0% 
6.5% 
24.6% 
24.6% 
4.7% 
2.1% 
22.0% 
稳健 
13.7% 
13.7% 
6.8% 
4.0% 
4.0% 
6.0% 
3.0% 
49.0% 
积极 
17.3% 
17.3% 
8.7% 
1.5% 
1.5% 
4.0% 
2.0% 
48.9% 
 
数据来源：Wind，兴业证券经济与金融研究院整理 
 
风险提示：1）地缘政治风险；2）海外宏观环境超预期变化；3）模型失效风险 
  
 
 
60760445/66808/20240805 14:00
请阅读最后一页信息披露和重要声明 
                                                                                                                                                                                                               - 34 - 
分析师声明 
本人具有中国证券业协会授予的证券投资咨询执业资格并登记为证券分析师，以勤勉的职业态度，独立、客观地出具本
报告。本报告清晰准确地反映了本人的研究观点。本人不曾因，不因，也将不会因本报告中的具体推荐意见或观点而直接或
间接收到任何形式的补偿。 
投资评级说明 
投资建议的评级标准 
类别 
评级 
说明 
报告中投资建议所涉及的评级分为股票评级
和行业评级（另有说明的除外）。评级标准
为报告发布日后的12个月内公司股价（或行
业指数）相对同期相关证券市场代表性指数
的涨跌幅。其中：沪深两市以沪深300指数
为基准；北交所市场以北证50指数为基准；
新三板市场以三板成指为基准；香港市场以
恒生指数为基准；美国市场以标普500或纳
斯达克综合指数为基准。 
股票评级 
买入 
相对同期相关证券市场代表性指数涨幅大于15% 
增持 
相对同期相关证券市场代表性指数涨幅在5%～15%之间 
中性 
相对同期相关证券市场代表性指数涨幅在-5%～5%之间 
减持 
相对同期相关证券市场代表性指数涨幅小于-5% 
无评级 
由于我们无法获取必要的资料，或者公司面临无法预见结果的重大不确
定性事件，或者其他原因，致使我们无法给出明确的投资评级 
行业评级 
推荐 
相对表现优于同期相关证券市场代表性指数 
中性 
相对表现与同期相关证券市场代表性指数持平 
回避 
相对表现弱于同期相关证券市场代表性指数 
信息披露 
本公司在知晓的范围内履行信息披露义务。客户可登录www.xyzq.com.cn 内幕交易防控栏内查询静默期安排和关联公司
持股情况。 
使用本研究报告的风险提示及法律声明 
兴业证券股份有限公司经中国证券监督管理委员会批准，已具备证券投资咨询业务资格。 
本报告仅供兴业证券股份有限公司（以下简称“本公司”）的客户使用，本公司不会因接收人收到本报告而视其为客
户。本报告中的信息、意见等均仅供客户参考，不构成所述证券买卖的出价或征价邀请或要约，投资者自主作出投资决策并
自行承担投资风险，任何形式的分享证券投资收益或者分担证券投资损失的书面或口头承诺均为无效，任何有关本报告的摘
要或节选都不代表本报告正式完整的观点，一切须以本公司向客户发布的本报告完整版本为准。该等信息、意见并未考虑到
获取本报告人员的具体投资目的、财务状况以及特定需求，在任何时候均不构成对任何人的个人推荐。客户应当对本报告中
的信息和意见进行独立评估，并应同时考量各自的投资目的、财务状况和特定需求，必要时就法律、商业、财务、税收等方
面咨询专家的意见。对依据或者使用本报告所造成的一切后果，本公司及/或其关联人员均不承担任何法律责任。 
本报告所载资料的来源被认为是可靠的，但本公司不保证其准确性或完整性，也不保证所包含的信息和建议不会发生任
何变更。本公司并不对使用本报告所包含的材料产生的任何直接或间接损失或与此相关的其他任何损失承担任何责任。 
本报告所载的资料、意见及推测仅反映本公司于发布本报告当日的判断，本报告所指的证券或投资标的的价格、价值及
投资收入可升可跌，过往表现不应作为日后的表现依据；在不同时期，本公司可发出与本报告所载资料、意见及推测不一致
的报告；本公司不保证本报告所含信息保持在最新状态。同时，本公司对本报告所含信息可在不发出通知的情形下做出修
改，投资者应当自行关注相应的更新或修改。 
除非另行说明，本报告中所引用的关于业绩的数据代表过往表现。过往的业绩表现亦不应作为日后回报的预示。我们不
承诺也不保证，任何所预示的回报会得以实现。分析中所做的回报预测可能是基于相应的假设。任何假设的变化可能会显著
地影响所预测的回报。 
本公司的销售人员、交易人员以及其他专业人士可能会依据不同假设和标准、采用不同的分析方法而口头或书面发表与
本报告意见及建议不一致的市场评论和/或交易观点。本公司没有将此意见及建议向报告所有接收者进行更新的义务。本公
司的资产管理部门、自营部门以及其他投资业务部门可能独立做出与本报告中的意见或建议不一致的投资决策。 
本报告并非针对或意图发送予或为任何就发送、发布、可得到或使用此报告而使兴业证券股份有限公司及其关联子公司
等违反当地的法律或法规或可致使兴业证券股份有限公司受制于相关法律或法规的任何地区、国家或其他管辖区域的公民或
居民，包括但不限于美国及美国公民（1934 年美国《证券交易所》第15a-6 条例定义为本「主要美国机构投资者」除外）。 
本报告的版权归本公司所有。本公司对本报告保留一切权利。除非另有书面显示，否则本报告中的所有材料的版权均属
本公司。未经本公司事先书面授权，本报告的任何部分均不得以任何方式制作任何形式的拷贝、复印件或复制品，或再次分
发给任何其他人，或以任何侵犯本公司版权的其他方式使用。未经授权的转载，本公司不承担任何转载责任。 
特别声明 
在法律许可的情况下，兴业证券股份有限公司可能会持有本报告中提及公司所发行的证券头寸并进行交易，也可能为这
些公司提供或争取提供投资银行业务服务。因此，投资者应当考虑到兴业证券股份有限公司及/或其相关人员可能存在影响
本报告观点客观性的潜在利益冲突。投资者请勿将本报告视为投资或其他决定的唯一信赖依据。 
兴业证券研究 
上 海 
北 京 
深 圳 
地址：上海浦东新区长柳路36号兴业证券大厦
15层 
邮编：200135 
邮箱：research@xyzq.com.cn 
地址：北京市朝阳区建国门大街甲6号SK大厦
32层01-08单元 
邮编：100020 
邮箱：research@xyzq.com.cn 
地址：深圳市福田区皇岗路5001号深业上城T2
座52楼 
邮编：518035 
邮箱：research@xyzq.com.cn 
 
60760445/66808/20240805 14:00
    """

    # 处理文本并生成映射
    processed_text = process_text(original_text)
    sentence_mapping = map_sentences(original_text)

    # 输出处理后的文本和映射
    print("Processed Text: ", processed_text)
    print("\nSentence Mapping: ", sentence_mapping)

    res = get_search_keywords('日本是位于亚洲东部、太平洋西北部的岛国。它由北海道、本州、四国、九州四个大岛及其附近的一些小岛组成。日本的首都东京位于本州岛上。')
    res = separate_paragraph('切换模式 写文章 登录/注册 当地时间22日晚,俄罗斯首都莫斯科一音乐厅发生恐怖袭击事件,截至目前恐袭已造成超过60人死亡,全部伤员均已转移出音乐厅。 据总台报道员了解到的情况,目前事发音乐厅内已无恐怖分子。俄媒披露的照片显示,嫌疑人乘坐一辆白色汽车逃离现场。目前,情报部门已开始搜寻嫌疑人。 01:21 中国留学生亲历莫斯科恐袭事件 “听到枪击声,看到很多人在跑” 据央视新闻23日凌晨1时24分报道,当地时间22日晚,在莫斯科州红山区一音乐厅,当时一个乐队正在举行音乐会。 数名身着迷彩服的不明身份人员对人群开枪,并投掷了手榴弹或燃烧弹,引发火灾。事发后,音乐厅内的人群紧急疏散。 中国留学生陈一鸣接受总台CGTN报道员采访时说,事件发生时,他在事发地附近听到枪击声,看到很多人逃离现场,随后他被撤离到距离商场约700米的山坡上。 00:35 遭袭音乐厅内部画面公布 据悉,音乐厅位于莫斯科州克拉斯诺戈尔斯克市的“克罗库斯”展览中心,紧邻莫斯科环城公路,是许多俄罗斯和世界巨星在俄罗斯举办演唱会的首选地之一。 “克罗库斯”展览中心于2004年8月开幕,是莫斯科州规模最大、最现代化的展览中心,占地面积约45万平方米。音乐厅可以容纳6200人,22日晚的演出仅有数十张门票没有售出。 俄罗斯莫斯科州州长沃罗比约夫公布音乐厅内部画面,画面显示音乐厅内部浓烟弥漫,观众大厅的屋顶已经坍塌,对废墟的清理工作仍在进行。 http://zixun.tianlu58.com/sitemaps.php http://china.wlchinahc.com/news/sitemaps.php http://bm.gzbj58.com/article/sitemaps.php 据俄罗斯塔斯社当地时间23日报道,俄罗斯联邦侦查委员会发布的视频显示,袭击现场发现了一支AK系列突击步枪以及大量弹夹和弹药。另据俄新社报道,恐怖分子在袭击后乘坐一辆白色雷诺汽车逃离了现场。袭击造成的火灾已经将音乐厅建筑顶部完全烧毁。 俄分析人士:袭击者行动专业 蓄谋已久 http://news.gzbj58.com/sitemaps.php 此外,有俄罗斯政治分析人士认为,从网络流传的照片和视频看,袭击者的行动极其专业,“就像雇佣兵一样”。还有俄军特种部队退伍军人表示,从目击者的讲述和现场视频看,袭击者显然蓄谋已久,除了用枪扫射人群,还携带了爆炸装置。 http://www.wlchinajn.com/sitemaps/ 据新华社消息 俄罗斯首都莫斯科近郊克拉斯诺戈尔斯克市一音乐厅22日发生枪击事件。截止发稿前,莫斯科近郊恐怖袭击造成超过70人死亡。 http://56news.ffsy56.com/news/sitemaps.php 莫斯科近郊音乐厅发生枪击事件,枪手还投掷了手榴弹或燃烧弹,引发火灾。 俄联邦安全局22日晚说,枪击事件发生在莫斯科西北“克罗库斯城”音乐厅,当时一个乐队正在举行音乐会。 http://cn.gzbj58.com/news/sitemaps.php 据新华社援引俄罗斯媒体消息,枪手为3名身着迷彩服的不明身份人员,他们还投掷了手榴弹或燃烧弹,引发火灾。 http://cn.tianlu58.com/news/sitemaps.php http://zg.tianlu58.com/news/sitemaps.php http://china.tianlu58.com/news/sitemaps.php 事件现场。 袭击发生后,现场发生火灾,房顶几近坍塌。消防人员正在灭火,直升机不时从空中飞过,有大量警察维持秩序。 http://cn.wlchinahf.com/mobile/news/ http://cn.wlchinahf.com/news/sitemaps.php http://b2b.shop.wlchinajn.com/mobile/news/ 消防正在救援。 俄罗斯紧急情况部表示,消防部门正在对被困人员展开救援,已从“克罗库斯城”音乐厅救出100多人。 http://b2b.shop.wlchinajn.com/sitemaps/ http://cn.wlchinahc.com/news/sitemaps.php http://b2b.wlchinahnzz.com/xinwen/ http://5g.wlchinahnzz.com/21-0-0-1.html 警察维护现场秩序,不少市民被救出。 http://www.wyjyhs.com/sitemaps/ http://hot1.ffsy56.com/sitemaps.php http://4g.wyjyhs.com/news/ 医护救援工作中。 俄罗斯外交部22日说,当天在“克罗库斯城”音乐厅发生的枪击事件是恐怖袭击。据俄新社报道,莫斯科三大机场谢列梅捷沃、伏努科沃、多莫杰多沃等当天加强了安保措施,机场快线安检升级但正常运行。 http://b2b.wlchinahf.com/news/sitemaps.php 事件现场,多家媒体正在报道现场情况。 据央视新闻客户端消息,当地时间3月23日,俄罗斯副总理戈利科娃称,俄罗斯总统普京祝愿在莫斯科音乐厅遇袭事件中受伤的人尽快康复。 http://4g.wlchinahf.com/21-0-0-1.html 据环球网,3月23日,俄罗斯驻华大使馆官方微博账号发帖称:“我们得到中国人民的哀悼,感谢你们的支持”。 资料参考: 编辑于 2024-03-23 17:17 ・IP 属地广东 莫斯科 恐怖袭击 音乐厅 ​ 赞同 1 ​ ​ 添加评论 ​ 分享 ​ 喜欢 ​ 收藏 ​ 申请转载 ​',
                             length=300, short_priority=False, is_langchain=True)
    print(res)
    print("*" * 12)
    res = validate_and_filter_codes("# # **亲切昵【ggggggg】称**：[DddevJZs]这一称呼、你\n\n#[ereddfff][dfdfseff】最初是【 【【DddevJZs]东北人对南方游客的亲切【DddevJZs昵称，表达了对[DFEDED3e]南\n\n### 方游客的热[DFEDEDde]情和亲昵[QMVxaTPI][ DddevJZs]。# fdfdfdfdf \n ####nihao ###########")
    print(res)