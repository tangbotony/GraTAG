import re
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from include.utils.text_utils import is_digit

def postprocessor(article: str):
    """
    对生成的文章进行后处理，内容包括：
    ①去掉开头的“标题：”字样
    ②去掉末尾的“（完）字样
    ③去掉文章中重复的句子
    ④去掉文章中的破折号（特指在段落开头或结尾处出现的破折号）
    ⑤部分段落中仅包含无意义的符号而没有实际的文字，需要删除
    TODO:⑥对于文章中引用的习总书记的话需要修改，确保和原话完全一致（需要和胡婕确定下具体方案）
    """
    # 修改内容一：去掉开头的“标题：”字样
    if article.startswith("标题："):
        article = article.lstrip("标题：")
    # 修改内容二：去掉结尾的“（完）”字样
    article = article.replace("（完）", "")
    article = article.replace("(完）", "")
    article = article.replace("（完)", "")
    article = article.replace("(完)", "")
    # 修改内容三：去掉文章中重复的句子
    article = "\n".join(sorted(set(article.split("\n")), key=article.split("\n").index))
    # 修改内容四：去掉文章中的破折号（特指在某一段开头或结尾出现的破折号）
    if article.find("\n——") >= 0:  # 段落开头出现的破折号，直接将破折号去掉即可
        article = article.replace("\n——", "\n")
    if article.find("——\n") >= 0:  # 段落结尾出现的破折号，将该破折号替换为句号
        article = article.replace("——\n", "。\n")
    if article.strip().startswith("——"):  # 文章开头（即第一段开头）出现的破折号
        article = article.replace("——", "", 1)
    if article.strip().endswith("——"):  # 文章结尾出现的破折号，替换为句号即可
        article = article[::-1].replace("——", "。", 1)[::-1]
    # 修改内容五：去掉仅包含无意义符号的段落
    split_article = article.split("\n")
    pieced_article = []
    for each_split in split_article:
        if re.match("新华社[\D]{2,4}[\d]{1,2}月[\d]{1,2}日", each_split) is not None:
            continue
        if (each_split.startswith("新华社记者") or each_split.startswith("记者")) and re.match(
                "[\d\D]*[\u4e00-\u9fa5]$", each_split) is not None:
            continue
        if re.search("[\u4e00-\u9fa5]", each_split) and len(each_split) > 0:  # 这一段有中文字符, 需要保留
            pieced_article.append(each_split)
    article = "\n".join(pieced_article)
    return article

def postprocess_timeline_split(text_lis:list):
    """
    对时间线拆分的子问题做后处理，删除编号，删除多问题形式只保留第一个问题
    """
    text_lis = [text for text in text_lis if text]
    timeline_split = []
    for text in text_lis:
        try:
            if "." in text and is_digit(text[0]):
                text = text.split(".")[1]
            if text.count("？") > 1:
                text = text.split("？")[0] + "？"
            # if "：" in text:
            #     continue
            text = text.lstrip().rstrip()
            assert text != ""
        except:
            pass 
        timeline_split.append(text)
    return timeline_split

def postprocess_multisplit_queries(text_lis:list):
    """
    针对QWEN2总是出现补充说明的情况，做数据后处理清洗，删除括号内容和备注内容。
    """
    post_queries = []
    for text in text_lis:
        punc_index = get_first_punctuation(text)
        text = text[:punc_index + 1]
        if text and "（" == text[0]:
            continue
        # if "：" in text:
        #     continue
        # if text and "（" in text[1:]:
        #     text = text.split("（")[0]
        # if text and "(" in text[1:]:
        #     text = text.split("(")[0]
        post_queries.append(text)
    return post_queries

def del_parenthesis(text_lis:list):
    """
    针对QWEN2总是出现补充说明的情况，做数据后处理清洗，删除括号内容和备注内容。
    """
    post_queries = []
    for text in text_lis:
        if text and "（" == text[0]:
            continue
        if text and "（" in text[1:]:
            text = text.split("（")[0]
        if text and "(" in text[1:]:
            text = text.split("(")[0]
        post_queries.append(text)
    return post_queries
        

def get_first_punctuation(text):
    """返回第一个 问号或者句号 的index"""
    index = re.search(r'\？|\。|\?|\！|\!', text).start() if re.search(r'\？|\。|\?|\！|\!', text) else len(text) - 1
    return index


def clean_and_eval(line):  # 这里不用try
    line = line.replace(": true", ": True")
    line = line.replace(": false", ": False")
    if "``json\n" in line:
        line = line.split("``json\n")[1]
    if "``python\n" in line:
        line = line.split("``python\n")[1]
    if "\n``" in line:
        line = line.split("\n``")[0]
    return eval(line)