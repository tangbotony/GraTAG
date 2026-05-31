# coding:utf-8
# 新语 应用算法路由
import logging
logging.basicConfig(format='线程：%(thread)d - %(levelname)s - %(asctime)s : %(message)s', level=logging.INFO)


# 调用基础续写任务
def basic_continue_write(selected_content, conteyut_above=None, context_below=None, output_length_rate=1.0, output_cnt=1 ):
    """
    :param selected_content: 续写选定的句子或段落
    :param context_above: 选定句子的上文，默认selected_content的3倍长度的上文
    :param context_below: 选定句子的下文，默认selected_content的3倍长度的下文
    :param output_length_rate: 续写的输出长度，默认为选定长度的3倍，例如选定一句，续写3句
    :param output_cnt: 输出的续写结果的个数
    :return: target_output_item string: 续写结果
    """
    if len(selected_content) == 0:
        raise ValueError("No selected content get!")  # 无选定输出报错
    # 以下是算法的处理逻辑
    target_output_item = "普通续写测试 xxx  xxx  xxx  xxx  xxx  xxx 续写测试结束"

    return target_output_item


# 调用专业续写任务
def pro_continue_write(selected_content, context_above, context_below, output_length_rate, output_cnt,
                       pro_setting_continue_direction, pro_setting_special_request, pro_setting_language_type):
    """
    :param selected_content: 续写选定的句子或段落
    :param context_above: 选定句子的上文，默认selected_content的3倍长度的上文
    :param context_below: 选定句子的下文，默认selected_content的3倍长度的下文
    :param output_length_rate:  续写的输出长度，默认为选定长度的3倍，例如选定一句，续写3句；
    :param output_cnt: 输出的续写结果的个数
    :param pro_setting_continue_direction: 专业续写参数：续写方向，dict格式 {"续写领域":xxx, "续写关键词":xxx...}
    :param pro_setting_special_request: 专业续写参数：特殊要求，String
    :param pro_setting_language_type: 语言风格，String， 830默认：新华体
    :return: target_output_item
    """
    if len(selected_content) == 0:
        raise ValueError("No selected content get!")  # 无选定输出报错

    target_output_item = "专业续写测试 xxx  xxx  xxx  xxx  xxx  xxx 专业续写测试结束"

    return target_output_item

# 调用基础扩写任务
def basic_expand_write(selected_content, context_above=None, context_below=None, output_length_rate=1.0):
    """
    :param selected_content: 扩写选定的句子或段落
    :param context_above: 扩写句子/段落的上文，默认selected_content的3倍长度的上文
    :param context_below: 扩写句子/段落的下文，默认selected_content的3倍长度的下文
    :param output_length_rate: 扩写的输出长度，默认为选定长度的3倍，例如选定一句，扩写3句
    :return: target_output_item string: 扩写结果
    """
    if len(selected_content) == 0:
        raise ValueError("No selected content get!")  # 无选定输出报错
    # 以下是算法的处理逻辑
    target_output_item = "扩写续写测试 xxx  xxx  xxx  xxx  xxx  xxx 扩写测试结束"

    return target_output_item


# 调用基础润色任务
def basic_polish_write(selected_content, context_above=None, context_below=None, polish_type=""):
    """
    :param selected_content: 润色选定的句子或段落
    :param context_above: 润色句子/段落的上文，默认selected_content的3倍长度的上文
    :param context_below: 润色句子/段落的下文，默认selected_content的3倍长度的下文
    :param polish_type: 润色类型
    :return:target_output_item
    """

    if len(selected_content) == 0:
        raise ValueError("No selected content get!")  # 无选定输出报错
    # 以下是算法的处理逻辑
    target_output_item = "润色结果xxx润色结果"

    return target_output_item


# 调用 AI 引证功能
def ai_reference_check(selected_content, context_above=None, context_below=None):
    """
    :param selected_content: 待检测的句子或段落
    :param context_above: 待检测句子/段落的上文，默认selected_content的3倍长度的上文
    :param context_below: 待检测句子/段落的下文，默认selected_content的3倍长度的下文
    :return: checked_item_dict # 检测声明摘录的句子字典，每一个key是selected_content中的句子或者段落
    """
    if len(selected_content) == 0:
        raise ValueError("No selected content get!")  # 无选定输出报错

    # 以下是算法的处理逻辑
    checked_item_dict = {
        "中国第一大岛，战略要地。": ["doc_id from ai DB","doc_id from ai DB","doc_id from ai DB"],
        "湾地区户籍登记人口为2360.31万人": ["doc_id from ai DB","doc_id from ai DB","doc_id from ai DB"]
    }

    return checked_item_dict






