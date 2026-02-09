import copy
import json
import re
import string
from typing import Union
import traceback
import requests
from tqdm import tqdm

from include.context.RagQAContext import RagQAContext, RagSingleQA, context_encode, context_decode
from include.config import DocQAConfig
from include.logger import ContextLogger
from multiprocessing.dummy import Pool
from include.logger import log
from include.utils.text_utils import get_md5, generate_random_string, poly_union


class DocSingleQA(RagSingleQA):
    def __init__(self, session_id, request_id, question_id, question, pro_flag, pdf_ids):
        super().__init__(session_id, request_id, question_id, question, pro_flag=pro_flag)
        self.name = "DocSingleQA"
        self._pdf_ids = pdf_ids
        self._doc_qa_pdf_names = []
        self.set_retrieval_field(retrieval_field={
            # 'iaar_database_kwargs': copy.deepcopy(DocQAConfig['IAAR_DataBase_Doc']['default_param']),
            'file_database_kwargs': copy.deepcopy(DocQAConfig['IAAR_DataBase_Doc']['file_database_default_param'])
        })
        self._doc_query_type = "具体问题"
        self._related_figtables = []
        self.set_QA_quickpass()
        self._figure_table_answer = []
        ContextLogger(self).warning("Query is: {}, Pdf_ids is {}:".format(question, pdf_ids))

    def set_QA_quickpass(self):
        self._quickpass = DocQAConfig['EXP_CONFIG']['is_fast']

    def get_pdf_ids(self):
        return self._pdf_ids

    def set_doc_query_type(self, doc_query_type):
        self._doc_query_type = doc_query_type

    def get_doc_query_type(self):
        return self._doc_query_type

    def set_related_figtable(self, figtable_list):
        self._related_figtables = figtable_list

    def get_related_figtable(self):
        return self._related_figtables

    def set_doc_qa_pdf_names(self, doc_qa_pdf_names):
        self._doc_qa_pdf_names = doc_qa_pdf_names

    def get_doc_qa_pdf_names(self):
        return self._doc_qa_pdf_names

    def set_figure_table_answer(self, figure_table_answer):
        self._figure_table_answer = figure_table_answer

    def get_figure_table_answer(self):
        return self._figure_table_answer


class DocQAContext(RagQAContext):
    def __init__(self,
                 session_id: string,
                 user_id: string = ''
                 ):
        """
        创建一个context对象
        :param session_id: 会话ID
        }
        """
        super().__init__(session_id, user_id)
        self.name = "DocQAContext"
        self.ref_answer = []  # 引证资料候选池

    def add_single_question(self, request_id, question_id, question, pro_flag=True, **kwargs):
        self._dialog[question_id] = DocSingleQA(
            self._session_id, request_id, question_id, question, pro_flag, kwargs.get('pdf_ids', []))
        self._cur_question_id = question_id

    def get_pdf_ids(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        question = rag_single_qa.get_pdf_ids()
        return question

    def get_doc_query_type(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        question = rag_single_qa.get_doc_query_type()
        return question

    def set_doc_query_type(self, doc_query_type, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_doc_query_type(doc_query_type)

    def set_doc_qa_pdf_names(self, doc_qa_pdf_names, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_doc_qa_pdf_names(doc_qa_pdf_names)

    def get_doc_qa_pdf_names(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_doc_qa_pdf_names()

    def set_figure_table_answer(self, figure_table_answer, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.set_figure_table_answer(figure_table_answer)

    def get_figure_table_answer(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_figure_table_answer()

    def set_related_figtable(self, figtable_list, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        rag_single_qa.set_related_figtable(figtable_list)

    def get_related_figtable(self, question_id=None):
        if not question_id:
            question_id = self._cur_question_id
        rag_single_qa = self._dialog[question_id]
        return rag_single_qa.get_related_figtable()

    def get_ref_answer(self, question_id=None, pro_flag=True):

        def get_chunk_split(split_input: dict):
            """
            调用文档拆分接口
            """
            headers = {
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Authorization': DocQAConfig["PDF_CHUNK_SPLIT"]["key"]
            }
            url = DocQAConfig["PDF_CHUNK_SPLIT"]["url"]
            payload = json.dumps(split_input)
            try:
                response = requests.request("POST", url=url, headers=headers, data=payload)
            except:
                traceback.print_exc()
            return json.loads(response.text)

        def get_delimiter(content: str):
            # 根据文档内容的语种返回分隔符，当文档内容中汉字占比达到50%以上时视为中文文档并返回"。"，其他情况返回". "
            try:
                if len(re.findall("[\u4e00-\u9fa5]", content)) / len(content) >= 0.5:
                    return "。"
            except ZeroDivisionError:
                return ". "
            return ". "

        def get_poly_from_ref_lib(page: Union[int, list], poly: list):
            if isinstance(page, int):
                return ["{},{}".format(page, str(poly)[1:-1])]
            else:
                return [["{}, {}".format(each_page, str(each_poly)[1:-1]) for each_page, each_poly in zip(page, poly)]]

        def get_ref_lib_from_doc_chunks(chunks_dict: dict, delimiter=". "):
            """
            将PDF拆分结果中所有纯文本部分重新组合成句。当PDF内容为英文时delimiter值为“. ”，为中文时delimiter值为“。”
            chunks_dict: PDF拆分接口的输出，格式如下(本方法的输出格式与chunks_dict完全相同)：
            {
                "{uid1}": [  // big chunk的uid
                    {
                        "uid": "{uuid}", // small chunk的id
                        "page": 1, // 元素所在PDF页码，方便回溯（当组合后的句子涉及跨页时，该属性值为list列表，如[1,2]）
                        "poly": [ // 区块坐标，矩形框，分别为 [left, top, right, bottom], 当组合后的句子涉及跨页时，该属性值为二维列表
                            0.25,
                            0.12,
                            0.5,
                            0.62
                        ],
                        "text": "While recently Multimodal Large Language Models (MM-LLMs) have made exciting strides, they mostly fall prey to the limitation of only inputside multimodal understanding, without the ability to produce content in multiple modalities. As we humans always perceive the world and communicate with people through various modalities, developing any-to-any MM-LLMs capable of accepting and delivering content in any modality becomes essential to human-level AI. To fill the gap, we present an end-to-end general-purpose any-to-any MM-LLM system, NExT-GPT. We connect an LLM with multimodal adaptors and different diffusion decoders, enabling NExT-GPT to perceive inputs and generate outputs in arbitrary combinations of t", // 标题文本
                        "type": "plain text" // chunk类型
                    },
                    {...},
                    {...},
                ],
                "{uid2}": [
                    {
                        "uid": "{uuid}"
                    }
                ],
                ...
            }
            """
            ref_lib = {}
            for key, value in chunks_dict.items():
                current_sentence = ""
                current_sentence_page = 1
                current_sentence_poly = [0, 0, 0, 0]
                if key not in ref_lib:
                    ref_lib[key] = []
                for each_line in value:
                    if isinstance(each_line, tuple) and len(each_line) == 2:
                        each_line = each_line[1]
                    current_sentence_page, current_sentence_poly = poly_union(current_sentence_page,
                                                                              each_line["page"],
                                                                              current_sentence_poly,
                                                                              each_line["poly"])

                    if each_line["type"] == "plain text":
                        temp_split = each_line["text"].split(delimiter)
                        current_piece = temp_split[0].strip()
                        for each_piece in temp_split:
                            try:
                                next_piece = temp_split[temp_split.index(each_piece) + 1].strip()
                            except IndexError:
                                if current_piece.endswith("-") and delimiter == ". ":
                                    current_sentence += current_piece.rstrip("-")
                                    break
                                else:
                                    current_sentence += current_piece + (" " if delimiter == ". " else "")
                                    break
                            current_sentence += (current_piece + delimiter)
                            current_sentence_page, current_sentence_poly = poly_union(current_sentence_page,
                                                                                      each_line["page"],
                                                                                      current_sentence_poly,
                                                                                      each_line["poly"])
                            current_piece = next_piece
                            ref_lib[key].append({
                                "uid": get_md5(current_sentence),
                                "page": current_sentence_page,
                                "poly": current_sentence_poly,
                                "text": current_sentence,
                                "type": "plain text"
                            })
                            current_sentence = ""
                            current_sentence_poly = [0, 0, 0, 0]
                            current_sentence_page = 0
                current_sentence_page, current_sentence_poly = poly_union(current_sentence_page,
                                                                          each_line["page"],
                                                                          current_sentence_poly,
                                                                          each_line["poly"])

                ref_lib[key].append({
                    "uid": get_md5(current_sentence),
                    "page": current_sentence_page,
                    "poly": current_sentence_poly,
                    "text": current_sentence,
                    "type": "plain text"
                })
            return ref_lib

        temp_ref_answer = super().get_ref_answer()
        if len(temp_ref_answer) == 0 or not pro_flag:
            self.ref_answer = temp_ref_answer
            return temp_ref_answer
        return_ref_answer = []
        chunk_split_input = []
        current_file_oss_id = temp_ref_answer[0]["oss_id"]
        for each_ref_answer in temp_ref_answer:
            if each_ref_answer["oss_id"].endswith(".txt"):
                return_ref_answer.append(each_ref_answer)
            else:
                if each_ref_answer != current_file_oss_id:
                    delimiter = get_delimiter(each_ref_answer["content"])
                    chunk_split_input.append({
                        "oss_id": each_ref_answer["oss_id"],
                        "news_id": each_ref_answer["news_id"],
                        "delimiter": delimiter,
                        "elements": []
                    })
                    current_file_oss_id = each_ref_answer["oss_id"]
                chunk_split_input[-1]["elements"].extend([
                    {
                        "page": int(each_element_poly.split(",")[0]),
                        "poly": eval(",".join(each_element_poly.split(",")[1:])),
                        "uid": get_md5(each_element_content)
                    } for each_element_poly, each_element_content in
                    zip(each_ref_answer["poly"], each_ref_answer["origin_content"])
                ])
        chunk_split_output = [get_chunk_split(each_input) for each_input in tqdm(chunk_split_input)]
        for each_doc_chunk_split_input, each_doc_chunk_split_output in zip(chunk_split_input, chunk_split_output):
            if "type" in each_doc_chunk_split_output or "error" in each_doc_chunk_split_output:
                continue
            try:
                ref_lib = get_ref_lib_from_doc_chunks(chunks_dict=each_doc_chunk_split_output,
                                                      delimiter=each_doc_chunk_split_input["delimiter"])
            except Exception as e:
                log.warning("拆分PDF重组失败，报错内容：{}，使用拆分前的big chunks进行挂载".format(e))
                self.ref_answer = temp_ref_answer
                return temp_ref_answer
            for each_ref_key, each_ref_value in ref_lib.items():
                return_ref_answer.extend([
                    {
                        "_id": "[{}]".format(generate_random_string(each_single_ref["text"], 8)),
                        "news_id": each_doc_chunk_split_input["news_id"],
                        "oss_id": each_doc_chunk_split_input["oss_id"],
                        "content": each_single_ref["text"],
                        "origin_content": "",
                        "poly": get_poly_from_ref_lib(each_single_ref["page"], each_single_ref["poly"])
                    } for each_single_ref in each_ref_value
                ])

        if not return_ref_answer:
            self.ref_answer = temp_ref_answer
            return temp_ref_answer
        self.ref_answer = return_ref_answer
        return return_ref_answer


if __name__ == '__main__':
    from include.utils.es_utils import save_to_es, load_from_es

    contextaaaaa = DocQAContext("?")
    contextaaaaa.add_single_question(1, 2, "。。。???", pdf_ids=[])
    contextaaaaa.add_references_result({'use_for_check_items': {'[YzbNJ0Qg]': {'id': '68d1c4b603293a21fd3b680fe2e1c636c97ef59db004d893a97c78c29a4e3e1e', 'description': '他亲口承认了包括玫瑰战争在内的诸多历史事件影响了他的写作过程,并最终反映到了小说之中,但是他亦坚持道:“书中并没有严格意义上的一对一关系,我更喜欢把历史当成一种调剂品,使得奇幻小说变得更加真实可靠,但绝不会简单地换个名字就挪到我的作品里面。”《冰与火之歌》中的多条情节线索和人物设定都与历史上的“玫瑰战争”相暗合,小说的两个主要家族:史塔克与兰尼斯特,分别代表了历史上的约克家族与兰开斯特家族。', 'title': '冰与火之歌(乔治·R·R·马丁所著小说) - 百度百科', 'url': 'https://baike.baidu.com/item/%E3%80%8A%E5%86%B0%E4%B8%8E%E7%81%AB%E4%B9%8B%E6%AD%8C%E3%80%8B/15415', 'theme': '冰与火之歌小说系列的故事背景是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[9EeAZjyr]': {'id': '250c77cdff2d30c78448b28d3fcac7914c728ba0da12a39c94e89eb1e445e308', 'description': '美剧 《冰与火之歌》 主要描述了在一片虚构的中世纪世界里所发生的一系列宫廷斗争、疆场厮杀、游历冒险和魔法抗衡的故事。《冰与火之歌》的故事发生在一个虚幻的中世纪世界,主要目光集中在西方的“日落王国”维斯特洛大陆 上,讲述那里的人在当时的政治背景下的遭遇和经历。第一条主线围绕着各方诸侯意图问鼎整个王国的权力中心 铁王座 而进行“权力的游戏”王朝斗争的故事展开。', 'title': '《冰与火之歌》主要讲了一个什么故事? - 百度知道', 'url': 'https://zhidao.baidu.com/question/1700240719689535908.html', 'theme': '冰与火之歌小说系列的故事主线是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[lBpKtwrS]': {'id': '089f219088d31b5ae5bb307e31cf7b641c674756b49890ed7951a844ec29da92', 'description': '扩展资料 《权力的游戏》,是美国 HBO电视网 制作推出的一部中世纪史诗奇幻题材的电视剧。该剧改编自美国作家 乔治·R·R·马丁 的奇幻小说《冰与火之歌》系列。《权力的游戏》以“创造奇迹”的高姿态打破了魔幻剧难以取得成功的美剧“魔咒”,一举颠覆所有好莱坞魔幻电影的创意水平。', 'title': '《冰与火之歌》主要讲了一个什么故事? - 百度知道', 'url': 'https://zhidao.baidu.com/question/1700240719689535908.html', 'theme': '冰与火之歌小说系列的故事主线是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[KZICqZGs]': {'id': 'f5dfebd7a49176a0f76739d5bd06e52367323fc02a3cbf9d3e68d5fb29b31176', 'description': '它给予演员、导演、编剧创意的无限可能,以其无限且有序的创作空间囊括了成千上万形象饱满的人物角色、怪诞独特充满想象的风土人情,其空间之完整、细节之丰富、叙事之恣意让人感叹。《冰与火之歌》是由美国作家乔治·R·R·马丁所著的严肃奇幻小说系列。该书系列首卷于1996年初由矮脚鸡图书公司在美国出版,全书计划共七卷,截至2014年共完成出版了五卷,被译为三十多种文字。', 'title': '《冰与火之歌》主要讲了一个什么故事? - 百度知道', 'url': 'https://zhidao.baidu.com/question/1700240719689535908.html', 'theme': '冰与火之歌小说系列的故事主线是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[2mMEVLs7]': {'id': '2822fbbd27d9267c4fcb0f346437f58a842aef5f8982224ca9acfe90accea150', 'description': '乔治·R.R·马丁  如果你是《权力的游戏》或者原著《冰与火之歌》的粉丝，一定听说了作者乔治·R.R·马丁史诗般的新作《火与血》出版了。《火与血》讲述了《权利的游戏》里坦格利安家族的历史，是此系列的第一卷。虽然在2013年的时候，马丁曾计划等这一系列全部完成后再出版，但后来还是决定先出个两卷本。', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[OVyT4zTx]': {'id': '598e25d030a0b0470957de1b564014badf558bbfb9917f5e6a01a75d40758450', 'description': '《火与血》英文版《冰与火之歌》改变的《权力的游戏》自2011年4月17日在美国HBO电视台首次播出以来，迎来连续多年的收视狂潮，在全世界赢得了无数忠实粉丝，2015年第67届艾美奖中破纪录地斩获12项大奖之后，今年又获得2018年第70届艾美奖最佳剧集奖。将于2019年4月播出的该系列第八季让很多人翘首以盼。如今《火与血》的出版，我们是不是又可以期待新作品的中文版引进，以及电视剧改编了呢？', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[x8T0Ogqg]': {'id': '8886849fcd6d419ea7978fefab2a2f660915dcb839514f9fcd0aaeae4493318c', 'description': '《火与血》描写的是《权游》中维斯特洛大陆的故事300年之前的事情。尽管差了几个世纪，然而根据最近马丁接受《娱乐周刊》（Entertainment Weekly）的采访来看，《火与血》中埋了一些关于《冰与火之歌》的小暗示。”确实有一些重要的小线索，不过我不会透露太多，读者必须自己去找出它们，然后辨别那些到底真的是暗示还是不过为了转移注意力的把戏。“马丁这样说。', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[qzY1q7J4]': {'id': 'f13d2ca9259530a58573cacc84c5fb70dda4faff24151c532084e219ed5e9a94', 'description': '我必须写完才行。“你都这么可爱地自责了，我们当然不会催你啦。马丁说《火与血》这本书对他来说是个很大的安慰，因为坦格利安家族系列完全是自己写出来的。很多人可能不太了解，此前的《冰与火之歌》是马丁和另一个作者伊莱奥·M·加西亚 Jr.合作写出，而这将是完全属于马丁自己的作品，是不是很期待呢？', 'title': '马丁谈新作《火与血》:我埋了很多《权力的游戏》的小暗示哦', 'url': 'https://baijiahao.baidu.com/s?id=1619534402804184832&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主题是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[C3c2k1s0]': {'id': '2578e904d8850e9b57037c82ef9de039d20ced87a857c7f1fa2cb241b82783da', 'description': '新客立减 登录 《冰与火之歌》主要情节 《冰与火之歌》是一部由美国作家乔治 · R· R· 马丁创作的史诗奇 幻小说系列,共有五卷。本书以中世纪为背景,讲述了七个王国 之间的权力斗争、家族恩怨以及古老的神秘力量的觉醒。以下是 《冰与火之歌》主要情节的梗概。第一卷:《权力的游戏》 本卷主要围绕斯塔克家族展开。史塔克家族是北境的贵族家族,由埃德 · 史塔克领导。', 'title': '《冰与火之歌》主要情节 - 百度文库', 'url': 'https://wenku.baidu.com/view/1c064f7f7a563c1ec5da50e2524de518974bd362.html', 'theme': '冰与火之歌小说系列的主要事件是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[cvbxsXlw]': {'id': '6a80f50753338326472c62d838743552382394c2082cc2def43aec4f67dc7cfc', 'description': '在这个充满快餐文化的时代，我们渴望着一些能够让我们陶冶情操、感受深刻的故事。而《冰与火之歌》（冰与火之歌）这本作品无疑是能够满足我们这种需求的经典之作。这本书集奇幻、政治、战争、爱情、背叛等元素于一身，讲述了一个虚构的中世纪欧洲风格的世界，探讨了人性、道德和权力的主题，给我们带来了一个充满惊喜和震撼的阅读体验。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[aJLxh2CK]': {'id': 'a63a8f2d35441e6c04a9696eeeee4972d1de495ef7fe5071de6e98d501f835fc', 'description': '在这个世界里，冰雪覆盖的北境、温暖宜人的南方、狂风肆虐的铁群岛、险峻的狭海、神秘的东方大陆等等，都成为了故事的背景。而书中许多角色也成为了经典，包括奈德·史塔克、提利昂·兰尼斯特、琼恩·雪诺、丹妮莉丝·坦格利安等等。他们的经历被交织在一起，构成了一个庞大而精致的史诗。《冰与火之歌》的故事情节复杂而精彩，这也是其最为吸引人的地方之一。在这个世界里，人人都有自己的目的和野心，都在为争夺铁王座而努力。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[CErsrEqh]': {'id': 'd9a230e5c840ef911c05b225790995bdacbcd4b914be1c3768fd331e20aa7933', 'description': '身为诸侯之一的奈德·史塔克，却在一场与势力更大的家族兰尼斯特的斗争中意外地失去了自己的生命。他的儿子罗柏成为了北方的领袖，并承诺要为他的父亲复仇。同时，南方的兰尼斯特家族也在为掌握铁王座而斗争，不惜手段地谋杀敌对家族的成员，包括国王。整个故事的发展都充满着政治斗争、背叛、恶行和权力之争。除了政治之争，书中也充满了奇幻元素。白步行者、龙、巨人、红女巫等等，都成为了书中令人难忘的角色和场景。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[Uopgpq1u]': {'id': '7df1dd54d2ffb1102ab7555a3a3026b70450bbcf41b605e9de07b628d5198ae4', 'description': '这些奇幻元素与现实世界的政治斗争融合在一起，使得整个故事更为生动有趣。除此之外，这本书中的角色也非常有特点。他们的性格、行为、语言都被塑造得十分立体鲜明，使得读者能够深入了解他们的内心世界。比如说提利昂·兰尼斯特，他是一个残忍却又聪明绝顶的角色，他用自己的智慧和手段掌控着家族的命运；琼恩·雪诺则是一个勇敢坚定、忠诚正直的角色，他在北方的长城上捍卫着王国的安全，面对的却是各种挑战和困难。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[CPUavslR]': {'id': 'd612db101a0dcecc3ee324cd09f31c883d5ce8b3f8506a995e36820ae46027a6', 'description': '¥15现货冰与火之歌全套平装15册1徽章淘宝旗舰店¥385.31¥664.2购买总之，《冰与火之歌》是一部令人着迷的作品，它融合了许多元素，以独特的方式呈现出一个充满人性、荣誉、背叛和权力之争的世界。作者乔治·R·R·马丁以他丰富的想象力和精湛的笔触，打造了一个宏大而又残酷的奇幻世界，让读者沉浸其中、忘却现实。如果你追求一个让你情感深刻、震撼人心的故事，那么《冰与火之歌》是一个非常好的选择。', 'title': '权力的游戏:《冰与火之歌》带你踏上宏大而残酷的奇幻之旅', 'url': 'https://baijiahao.baidu.com/s?id=1763030693842392952&wfr=spider&for=pc', 'theme': '冰与火之歌小说系列的主要情节转折点有哪些？', 'source': 'net_kwargs', 'source_id': ''}, '[6uN8Ofsf]': {'id': '3a3c2e1c364d5c5de82e4847f7e2482db66086be31c00e6a19a26eb990427dc1', 'description': '新客立减 登录 冰与火之歌奇幻文学的经典之作 《冰与火之歌:奇幻文学的经典之作》 《冰与火之歌》是美国作家乔治 · R· R· 马丁创作的一部奇幻文学巨著,被誉为现代奇幻文学的经典之作。小说通过扑朔迷离的情节、复杂细 腻的人物关系、宏大壮阔的世界观,展现出了一个瑰丽而残酷的中世 纪式幻想世界。', 'title': '冰与火之歌奇幻文学的经典之作 - 百度文库', 'url': 'https://wenku.baidu.com/view/509323cae75c3b3567ec102de2bd960591c6d92c.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[vjP3Zc0O]': {'id': 'ef21cadf0552dfe34ca737d3624e0512f6fb910fea2bb61244c8fda81c5f54c3', 'description': '冰与火之歌系列共包括《权力的游戏》、《列王的纷争》、《冰雨 的风暴》、《群鸦的盛宴》、《魔龙的狂舞》以及尚未出版的两部续 作。该系列小说出版以来,在全球范围内掀起了一股奇幻文学热潮,被翻译成多种语言,并改编成成功的电视剧《权力的游戏》。《冰与火之歌》以细腻入微的人物刻画和复杂的家族关系网络为特 点。', 'title': '冰与火之歌奇幻文学的经典之作 - 百度文库', 'url': 'https://wenku.baidu.com/view/509323cae75c3b3567ec102de2bd960591c6d92c.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[bxnKfwkq]': {'id': 'aaee183300cd270bea7a6bc151bf699ebc0f55d18b7e5eeda408060595f7ca63', 'description': '冰与火之歌:权谋、荣耀与欲望的恢弘史诗 介绍 《冰与火之歌》是美国作家乔治·R·R·马丁创作的一部史诗奇幻小说系列,被广 泛誉为现代奇幻文学的巅峰之作。该系列小说以中世纪欧洲为背景,具有浓厚 的政治阴谋、荣耀和欲望的元素,引发了全球读者群体的狂热追捧。故事背景 故事发生在虚构的七大王国大陆上。数个封建领主家族和一个暴君共同统治这 片土地。', 'title': '《冰与火之歌》:权谋、荣耀与欲望的恢弘史诗 - 百度文库', 'url': 'https://wenku.baidu.com/view/45133a45d6bbfd0a79563c1ec5da50e2534dd10d.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}, '[zy78I8QC]': {'id': '949bc6cf1f089fa628c07c435e2901f7d1de5eb46b7a4b59e8d83f2431e3ac21', 'description': '3.龙母:作为流亡贵族的最后一名幸存者,她带领三条幼龙逐渐成长,并向 铁王座发起挑战。她是荣耀与欲望的象征之一。情节剧变和复杂关系 1.纷争与叛乱:各个家族、各种势力之间展开了相互争斗、背叛和内讧的故 事情节。读者将跟随主人公们经历暗黑而曲折的命运。', 'title': '《冰与火之歌》:权谋、荣耀与欲望的恢弘史诗 - 百度文库', 'url': 'https://wenku.baidu.com/view/45133a45d6bbfd0a79563c1ec5da50e2534dd10d.html', 'theme': '冰与火之歌小说系列对现代奇幻小说的影响是什么？', 'source': 'net_kwargs', 'source_id': ''}}, 'use_for_check_items_content_dic': {'他亲口承认了包括玫瑰战争在内的诸多历史事件影响了他的写作过程,并最终反映到了小说之中,但是他亦坚持道:“书中并没有严格意义上的一对一关系,我更喜欢把历史当成一种调剂品,使得奇幻小说变得更加真实可靠,但绝不会简单地换个名字就挪到我的作品里面。”《冰与火之歌》中的多条情节线索和人物设定都与历史上的“玫瑰战争”相暗合,小说的两个主要家族:史塔克与兰尼斯特,分别代表了历史上的约克家族与兰开斯特家族。': '[YzbNJ0Qg]', '美剧 《冰与火之歌》 主要描述了在一片虚构的中世纪世界里所发生的一系列宫廷斗争、疆场厮杀、游历冒险和魔法抗衡的故事。《冰与火之歌》的故事发生在一个虚幻的中世纪世界,主要目光集中在西方的“日落王国”维斯特洛大陆 上,讲述那里的人在当时的政治背景下的遭遇和经历。第一条主线围绕着各方诸侯意图问鼎整个王国的权力中心 铁王座 而进行“权力的游戏”王朝斗争的故事展开。': '[9EeAZjyr]', '扩展资料 《权力的游戏》,是美国 HBO电视网 制作推出的一部中世纪史诗奇幻题材的电视剧。该剧改编自美国作家 乔治·R·R·马丁 的奇幻小说《冰与火之歌》系列。《权力的游戏》以“创造奇迹”的高姿态打破了魔幻剧难以取得成功的美剧“魔咒”,一举颠覆所有好莱坞魔幻电影的创意水平。': '[lBpKtwrS]', '它给予演员、导演、编剧创意的无限可能,以其无限且有序的创作空间囊括了成千上万形象饱满的人物角色、怪诞独特充满想象的风土人情,其空间之完整、细节之丰富、叙事之恣意让人感叹。《冰与火之歌》是由美国作家乔治·R·R·马丁所著的严肃奇幻小说系列。该书系列首卷于1996年初由矮脚鸡图书公司在美国出版,全书计划共七卷,截至2014年共完成出版了五卷,被译为三十多种文字。': '[KZICqZGs]', '乔治·R.R·马丁  如果你是《权力的游戏》或者原著《冰与火之歌》的粉丝，一定听说了作者乔治·R.R·马丁史诗般的新作《火与血》出版了。《火与血》讲述了《权利的游戏》里坦格利安家族的历史，是此系列的第一卷。虽然在2013年的时候，马丁曾计划等这一系列全部完成后再出版，但后来还是决定先出个两卷本。': '[2mMEVLs7]', '《火与血》英文版《冰与火之歌》改变的《权力的游戏》自2011年4月17日在美国HBO电视台首次播出以来，迎来连续多年的收视狂潮，在全世界赢得了无数忠实粉丝，2015年第67届艾美奖中破纪录地斩获12项大奖之后，今年又获得2018年第70届艾美奖最佳剧集奖。将于2019年4月播出的该系列第八季让很多人翘首以盼。如今《火与血》的出版，我们是不是又可以期待新作品的中文版引进，以及电视剧改编了呢？': '[OVyT4zTx]', '《火与血》描写的是《权游》中维斯特洛大陆的故事300年之前的事情。尽管差了几个世纪，然而根据最近马丁接受《娱乐周刊》（Entertainment Weekly）的采访来看，《火与血》中埋了一些关于《冰与火之歌》的小暗示。”确实有一些重要的小线索，不过我不会透露太多，读者必须自己去找出它们，然后辨别那些到底真的是暗示还是不过为了转移注意力的把戏。“马丁这样说。': '[x8T0Ogqg]', '我必须写完才行。“你都这么可爱地自责了，我们当然不会催你啦。马丁说《火与血》这本书对他来说是个很大的安慰，因为坦格利安家族系列完全是自己写出来的。很多人可能不太了解，此前的《冰与火之歌》是马丁和另一个作者伊莱奥·M·加西亚 Jr.合作写出，而这将是完全属于马丁自己的作品，是不是很期待呢？': '[qzY1q7J4]', '新客立减 登录 《冰与火之歌》主要情节 《冰与火之歌》是一部由美国作家乔治 · R· R· 马丁创作的史诗奇 幻小说系列,共有五卷。本书以中世纪为背景,讲述了七个王国 之间的权力斗争、家族恩怨以及古老的神秘力量的觉醒。以下是 《冰与火之歌》主要情节的梗概。第一卷:《权力的游戏》 本卷主要围绕斯塔克家族展开。史塔克家族是北境的贵族家族,由埃德 · 史塔克领导。': '[C3c2k1s0]', '在这个充满快餐文化的时代，我们渴望着一些能够让我们陶冶情操、感受深刻的故事。而《冰与火之歌》（冰与火之歌）这本作品无疑是能够满足我们这种需求的经典之作。这本书集奇幻、政治、战争、爱情、背叛等元素于一身，讲述了一个虚构的中世纪欧洲风格的世界，探讨了人性、道德和权力的主题，给我们带来了一个充满惊喜和震撼的阅读体验。': '[cvbxsXlw]', '在这个世界里，冰雪覆盖的北境、温暖宜人的南方、狂风肆虐的铁群岛、险峻的狭海、神秘的东方大陆等等，都成为了故事的背景。而书中许多角色也成为了经典，包括奈德·史塔克、提利昂·兰尼斯特、琼恩·雪诺、丹妮莉丝·坦格利安等等。他们的经历被交织在一起，构成了一个庞大而精致的史诗。《冰与火之歌》的故事情节复杂而精彩，这也是其最为吸引人的地方之一。在这个世界里，人人都有自己的目的和野心，都在为争夺铁王座而努力。': '[aJLxh2CK]', '身为诸侯之一的奈德·史塔克，却在一场与势力更大的家族兰尼斯特的斗争中意外地失去了自己的生命。他的儿子罗柏成为了北方的领袖，并承诺要为他的父亲复仇。同时，南方的兰尼斯特家族也在为掌握铁王座而斗争，不惜手段地谋杀敌对家族的成员，包括国王。整个故事的发展都充满着政治斗争、背叛、恶行和权力之争。除了政治之争，书中也充满了奇幻元素。白步行者、龙、巨人、红女巫等等，都成为了书中令人难忘的角色和场景。': '[CErsrEqh]', '这些奇幻元素与现实世界的政治斗争融合在一起，使得整个故事更为生动有趣。除此之外，这本书中的角色也非常有特点。他们的性格、行为、语言都被塑造得十分立体鲜明，使得读者能够深入了解他们的内心世界。比如说提利昂·兰尼斯特，他是一个残忍却又聪明绝顶的角色，他用自己的智慧和手段掌控着家族的命运；琼恩·雪诺则是一个勇敢坚定、忠诚正直的角色，他在北方的长城上捍卫着王国的安全，面对的却是各种挑战和困难。': '[Uopgpq1u]', '¥15现货冰与火之歌全套平装15册1徽章淘宝旗舰店¥385.31¥664.2购买总之，《冰与火之歌》是一部令人着迷的作品，它融合了许多元素，以独特的方式呈现出一个充满人性、荣誉、背叛和权力之争的世界。作者乔治·R·R·马丁以他丰富的想象力和精湛的笔触，打造了一个宏大而又残酷的奇幻世界，让读者沉浸其中、忘却现实。如果你追求一个让你情感深刻、震撼人心的故事，那么《冰与火之歌》是一个非常好的选择。': '[CPUavslR]', '新客立减 登录 冰与火之歌奇幻文学的经典之作 《冰与火之歌:奇幻文学的经典之作》 《冰与火之歌》是美国作家乔治 · R· R· 马丁创作的一部奇幻文学巨著,被誉为现代奇幻文学的经典之作。小说通过扑朔迷离的情节、复杂细 腻的人物关系、宏大壮阔的世界观,展现出了一个瑰丽而残酷的中世 纪式幻想世界。': '[6uN8Ofsf]', '冰与火之歌系列共包括《权力的游戏》、《列王的纷争》、《冰雨 的风暴》、《群鸦的盛宴》、《魔龙的狂舞》以及尚未出版的两部续 作。该系列小说出版以来,在全球范围内掀起了一股奇幻文学热潮,被翻译成多种语言,并改编成成功的电视剧《权力的游戏》。《冰与火之歌》以细腻入微的人物刻画和复杂的家族关系网络为特 点。': '[vjP3Zc0O]', '冰与火之歌:权谋、荣耀与欲望的恢弘史诗 介绍 《冰与火之歌》是美国作家乔治·R·R·马丁创作的一部史诗奇幻小说系列,被广 泛誉为现代奇幻文学的巅峰之作。该系列小说以中世纪欧洲为背景,具有浓厚 的政治阴谋、荣耀和欲望的元素,引发了全球读者群体的狂热追捧。故事背景 故事发生在虚构的七大王国大陆上。数个封建领主家族和一个暴君共同统治这 片土地。': '[bxnKfwkq]', '3.龙母:作为流亡贵族的最后一名幸存者,她带领三条幼龙逐渐成长,并向 铁王座发起挑战。她是荣耀与欲望的象征之一。情节剧变和复杂关系 1.纷争与叛乱:各个家族、各种势力之间展开了相互争斗、背叛和内讧的故 事情节。读者将跟随主人公们经历暗黑而曲折的命运。': '[zy78I8QC]'}, 'use_for_check_items_opinion_similarity_dic': {'他亲口承认了包括玫瑰战争在内的诸多历史事件影响了他的写作过程,并最终反映到了小说之中,但是他亦坚持道:“书中并没有严格意义上的一对一关系,我更喜欢把历史当成一种调剂品,使得奇幻小说变得更加真实可靠,但绝不会简单地换个名字就挪到我的作品里面。”《冰与火之歌》中的多条情节线索和人物设定都与历史上的“玫瑰战争”相暗合,小说的两个主要家族:史塔克与兰尼斯特,分别代表了历史上的约克家族与兰开斯特家族。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5830847024917603, '冰与火之歌小说系列的故事主线是什么？': 0.5805013179779053, '冰与火之歌小说系列的主要事件是什么？': 0.571262001991272, '冰与火之歌小说系列的故事背景是什么？': 0.5941958427429199, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5606472492218018, '冰与火之歌小说系列的主题是什么？': 0.546190083026886, '冰与火之歌小说系列的成功因素有哪些？': 0.5448422431945801, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5118087530136108, '乔治·R·R·马丁是谁？': 0.25151216983795166}, '美剧 《冰与火之歌》 主要描述了在一片虚构的中世纪世界里所发生的一系列宫廷斗争、疆场厮杀、游历冒险和魔法抗衡的故事。《冰与火之歌》的故事发生在一个虚幻的中世纪世界,主要目光集中在西方的“日落王国”维斯特洛大陆 上,讲述那里的人在当时的政治背景下的遭遇和经历。第一条主线围绕着各方诸侯意图问鼎整个王国的权力中心 铁王座 而进行“权力的游戏”王朝斗争的故事展开。': {'冰与火之歌小说系列的主要人物有哪些？': 0.522656261920929, '冰与火之歌小说系列的故事主线是什么？': 0.5978350043296814, '冰与火之歌小说系列的主要事件是什么？': 0.5671646595001221, '冰与火之歌小说系列的故事背景是什么？': 0.5610002279281616, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5271753072738647, '冰与火之歌小说系列的主题是什么？': 0.5246851444244385, '冰与火之歌小说系列的成功因素有哪些？': 0.5023845434188843, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4330064356327057, '乔治·R·R·马丁是谁？': 0.18719661235809326}, '扩展资料 《权力的游戏》,是美国 HBO电视网 制作推出的一部中世纪史诗奇幻题材的电视剧。该剧改编自美国作家 乔治·R·R·马丁 的奇幻小说《冰与火之歌》系列。《权力的游戏》以“创造奇迹”的高姿态打破了魔幻剧难以取得成功的美剧“魔咒”,一举颠覆所有好莱坞魔幻电影的创意水平。': {'冰与火之歌小说系列的主要人物有哪些？': 0.47262707352638245, '冰与火之歌小说系列的故事主线是什么？': 0.49120235443115234, '冰与火之歌小说系列的主要事件是什么？': 0.5062974691390991, '冰与火之歌小说系列的故事背景是什么？': 0.5224155187606812, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.4569784700870514, '冰与火之歌小说系列的主题是什么？': 0.4918754994869232, '冰与火之歌小说系列的成功因素有哪些？': 0.4785429835319519, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.41328859329223633, '乔治·R·R·马丁是谁？': 0.3317170739173889}, '它给予演员、导演、编剧创意的无限可能,以其无限且有序的创作空间囊括了成千上万形象饱满的人物角色、怪诞独特充满想象的风土人情,其空间之完整、细节之丰富、叙事之恣意让人感叹。《冰与火之歌》是由美国作家乔治·R·R·马丁所著的严肃奇幻小说系列。该书系列首卷于1996年初由矮脚鸡图书公司在美国出版,全书计划共七卷,截至2014年共完成出版了五卷,被译为三十多种文字。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5424028038978577, '冰与火之歌小说系列的故事主线是什么？': 0.5208942890167236, '冰与火之歌小说系列的主要事件是什么？': 0.530415952205658, '冰与火之歌小说系列的故事背景是什么？': 0.5498812198638916, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.48795801401138306, '冰与火之歌小说系列的主题是什么？': 0.5245355367660522, '冰与火之歌小说系列的成功因素有哪些？': 0.5352681279182434, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5294638276100159, '乔治·R·R·马丁是谁？': 0.3067325949668884}, '乔治·R.R·马丁  如果你是《权力的游戏》或者原著《冰与火之歌》的粉丝，一定听说了作者乔治·R.R·马丁史诗般的新作《火与血》出版了。《火与血》讲述了《权利的游戏》里坦格利安家族的历史，是此系列的第一卷。虽然在2013年的时候，马丁曾计划等这一系列全部完成后再出版，但后来还是决定先出个两卷本。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5470727682113647, '冰与火之歌小说系列的故事主线是什么？': 0.5303211212158203, '冰与火之歌小说系列的主要事件是什么？': 0.5636633634567261, '冰与火之歌小说系列的故事背景是什么？': 0.559965193271637, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.4808250665664673, '冰与火之歌小说系列的主题是什么？': 0.5303019285202026, '冰与火之歌小说系列的成功因素有哪些？': 0.5003072619438171, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4798562824726105, '乔治·R·R·马丁是谁？': 0.571890652179718}, '《火与血》英文版《冰与火之歌》改变的《权力的游戏》自2011年4月17日在美国HBO电视台首次播出以来，迎来连续多年的收视狂潮，在全世界赢得了无数忠实粉丝，2015年第67届艾美奖中破纪录地斩获12项大奖之后，今年又获得2018年第70届艾美奖最佳剧集奖。将于2019年4月播出的该系列第八季让很多人翘首以盼。如今《火与血》的出版，我们是不是又可以期待新作品的中文版引进，以及电视剧改编了呢？': {'冰与火之歌小说系列的主要人物有哪些？': 0.49481016397476196, '冰与火之歌小说系列的故事主线是什么？': 0.4986376166343689, '冰与火之歌小说系列的主要事件是什么？': 0.5366332530975342, '冰与火之歌小说系列的故事背景是什么？': 0.5315499305725098, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5149340033531189, '冰与火之歌小说系列的主题是什么？': 0.5138964056968689, '冰与火之歌小说系列的成功因素有哪些？': 0.5063655972480774, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4651692807674408, '乔治·R·R·马丁是谁？': 0.30041244626045227}, '《火与血》描写的是《权游》中维斯特洛大陆的故事300年之前的事情。尽管差了几个世纪，然而根据最近马丁接受《娱乐周刊》（Entertainment Weekly）的采访来看，《火与血》中埋了一些关于《冰与火之歌》的小暗示。”确实有一些重要的小线索，不过我不会透露太多，读者必须自己去找出它们，然后辨别那些到底真的是暗示还是不过为了转移注意力的把戏。“马丁这样说。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5312796235084534, '冰与火之歌小说系列的故事主线是什么？': 0.607370138168335, '冰与火之歌小说系列的主要事件是什么？': 0.590825080871582, '冰与火之歌小说系列的故事背景是什么？': 0.6291518211364746, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5607295632362366, '冰与火之歌小说系列的主题是什么？': 0.5580481886863708, '冰与火之歌小说系列的成功因素有哪些？': 0.5445112586021423, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5173963308334351, '乔治·R·R·马丁是谁？': 0.34022295475006104}, '我必须写完才行。“你都这么可爱地自责了，我们当然不会催你啦。马丁说《火与血》这本书对他来说是个很大的安慰，因为坦格利安家族系列完全是自己写出来的。很多人可能不太了解，此前的《冰与火之歌》是马丁和另一个作者伊莱奥·M·加西亚 Jr.合作写出，而这将是完全属于马丁自己的作品，是不是很期待呢？': {'冰与火之歌小说系列的主要人物有哪些？': 0.5334891676902771, '冰与火之歌小说系列的故事主线是什么？': 0.5522834062576294, '冰与火之歌小说系列的主要事件是什么？': 0.5461595058441162, '冰与火之歌小说系列的故事背景是什么？': 0.5646006464958191, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5037646889686584, '冰与火之歌小说系列的主题是什么？': 0.5503731966018677, '冰与火之歌小说系列的成功因素有哪些？': 0.5187556743621826, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4974684715270996, '乔治·R·R·马丁是谁？': 0.4253619313240051}, '新客立减 登录 《冰与火之歌》主要情节 《冰与火之歌》是一部由美国作家乔治 · R· R· 马丁创作的史诗奇 幻小说系列,共有五卷。本书以中世纪为背景,讲述了七个王国 之间的权力斗争、家族恩怨以及古老的神秘力量的觉醒。以下是 《冰与火之歌》主要情节的梗概。第一卷:《权力的游戏》 本卷主要围绕斯塔克家族展开。史塔克家族是北境的贵族家族,由埃德 · 史塔克领导。': {'冰与火之歌小说系列的主要人物有哪些？': 0.6290047764778137, '冰与火之歌小说系列的故事主线是什么？': 0.6474533081054688, '冰与火之歌小说系列的主要事件是什么？': 0.6427901387214661, '冰与火之歌小说系列的故事背景是什么？': 0.6317615509033203, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.6134090423583984, '冰与火之歌小说系列的主题是什么？': 0.6010677814483643, '冰与火之歌小说系列的成功因素有哪些？': 0.5466427206993103, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.48217761516571045, '乔治·R·R·马丁是谁？': 0.25230029225349426}, '在这个充满快餐文化的时代，我们渴望着一些能够让我们陶冶情操、感受深刻的故事。而《冰与火之歌》（冰与火之歌）这本作品无疑是能够满足我们这种需求的经典之作。这本书集奇幻、政治、战争、爱情、背叛等元素于一身，讲述了一个虚构的中世纪欧洲风格的世界，探讨了人性、道德和权力的主题，给我们带来了一个充满惊喜和震撼的阅读体验。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5589199662208557, '冰与火之歌小说系列的故事主线是什么？': 0.6032648086547852, '冰与火之歌小说系列的主要事件是什么？': 0.5889384746551514, '冰与火之歌小说系列的故事背景是什么？': 0.6350045800209045, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5445408225059509, '冰与火之歌小说系列的主题是什么？': 0.603825569152832, '冰与火之歌小说系列的成功因素有哪些？': 0.5973975658416748, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.567415714263916, '乔治·R·R·马丁是谁？': 0.2542561888694763}, '在这个世界里，冰雪覆盖的北境、温暖宜人的南方、狂风肆虐的铁群岛、险峻的狭海、神秘的东方大陆等等，都成为了故事的背景。而书中许多角色也成为了经典，包括奈德·史塔克、提利昂·兰尼斯特、琼恩·雪诺、丹妮莉丝·坦格利安等等。他们的经历被交织在一起，构成了一个庞大而精致的史诗。《冰与火之歌》的故事情节复杂而精彩，这也是其最为吸引人的地方之一。在这个世界里，人人都有自己的目的和野心，都在为争夺铁王座而努力。': {'冰与火之歌小说系列的主要人物有哪些？': 0.6508440971374512, '冰与火之歌小说系列的故事主线是什么？': 0.654075026512146, '冰与火之歌小说系列的主要事件是什么？': 0.6263918876647949, '冰与火之歌小说系列的故事背景是什么？': 0.6792794466018677, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.6192997694015503, '冰与火之歌小说系列的主题是什么？': 0.617631196975708, '冰与火之歌小说系列的成功因素有哪些？': 0.6464900970458984, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5506643056869507, '乔治·R·R·马丁是谁？': 0.2508317232131958}, '身为诸侯之一的奈德·史塔克，却在一场与势力更大的家族兰尼斯特的斗争中意外地失去了自己的生命。他的儿子罗柏成为了北方的领袖，并承诺要为他的父亲复仇。同时，南方的兰尼斯特家族也在为掌握铁王座而斗争，不惜手段地谋杀敌对家族的成员，包括国王。整个故事的发展都充满着政治斗争、背叛、恶行和权力之争。除了政治之争，书中也充满了奇幻元素。白步行者、龙、巨人、红女巫等等，都成为了书中令人难忘的角色和场景。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5198290348052979, '冰与火之歌小说系列的故事主线是什么？': 0.49745866656303406, '冰与火之歌小说系列的主要事件是什么？': 0.5428277254104614, '冰与火之歌小说系列的故事背景是什么？': 0.5097785592079163, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5069944858551025, '冰与火之歌小说系列的主题是什么？': 0.48197710514068604, '冰与火之歌小说系列的成功因素有哪些？': 0.4867812395095825, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4208918809890747, '乔治·R·R·马丁是谁？': 0.2670937478542328}, '这些奇幻元素与现实世界的政治斗争融合在一起，使得整个故事更为生动有趣。除此之外，这本书中的角色也非常有特点。他们的性格、行为、语言都被塑造得十分立体鲜明，使得读者能够深入了解他们的内心世界。比如说提利昂·兰尼斯特，他是一个残忍却又聪明绝顶的角色，他用自己的智慧和手段掌控着家族的命运；琼恩·雪诺则是一个勇敢坚定、忠诚正直的角色，他在北方的长城上捍卫着王国的安全，面对的却是各种挑战和困难。': {'冰与火之歌小说系列的主要人物有哪些？': 0.45925062894821167, '冰与火之歌小说系列的故事主线是什么？': 0.45566484332084656, '冰与火之歌小说系列的主要事件是什么？': 0.44420769810676575, '冰与火之歌小说系列的故事背景是什么？': 0.4719628691673279, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.44721806049346924, '冰与火之歌小说系列的主题是什么？': 0.44245555996894836, '冰与火之歌小说系列的成功因素有哪些？': 0.5321061611175537, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.4622625410556793, '乔治·R·R·马丁是谁？': 0.27265214920043945}, '¥15现货冰与火之歌全套平装15册1徽章淘宝旗舰店¥385.31¥664.2购买总之，《冰与火之歌》是一部令人着迷的作品，它融合了许多元素，以独特的方式呈现出一个充满人性、荣誉、背叛和权力之争的世界。作者乔治·R·R·马丁以他丰富的想象力和精湛的笔触，打造了一个宏大而又残酷的奇幻世界，让读者沉浸其中、忘却现实。如果你追求一个让你情感深刻、震撼人心的故事，那么《冰与火之歌》是一个非常好的选择。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5492427349090576, '冰与火之歌小说系列的故事主线是什么？': 0.5673253536224365, '冰与火之歌小说系列的主要事件是什么？': 0.566727876663208, '冰与火之歌小说系列的故事背景是什么？': 0.5986763834953308, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5307523608207703, '冰与火之歌小说系列的主题是什么？': 0.5659594535827637, '冰与火之歌小说系列的成功因素有哪些？': 0.5745295286178589, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5596000552177429, '乔治·R·R·马丁是谁？': 0.4660329520702362}, '新客立减 登录 冰与火之歌奇幻文学的经典之作 《冰与火之歌:奇幻文学的经典之作》 《冰与火之歌》是美国作家乔治 · R· R· 马丁创作的一部奇幻文学巨著,被誉为现代奇幻文学的经典之作。小说通过扑朔迷离的情节、复杂细 腻的人物关系、宏大壮阔的世界观,展现出了一个瑰丽而残酷的中世 纪式幻想世界。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5250936150550842, '冰与火之歌小说系列的故事主线是什么？': 0.5156024098396301, '冰与火之歌小说系列的主要事件是什么？': 0.5273780822753906, '冰与火之歌小说系列的故事背景是什么？': 0.5429602861404419, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5077226758003235, '冰与火之歌小说系列的主题是什么？': 0.515972375869751, '冰与火之歌小说系列的成功因素有哪些？': 0.5131537914276123, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5270513296127319, '乔治·R·R·马丁是谁？': 0.2713403105735779}, '冰与火之歌系列共包括《权力的游戏》、《列王的纷争》、《冰雨 的风暴》、《群鸦的盛宴》、《魔龙的狂舞》以及尚未出版的两部续 作。该系列小说出版以来,在全球范围内掀起了一股奇幻文学热潮,被翻译成多种语言,并改编成成功的电视剧《权力的游戏》。《冰与火之歌》以细腻入微的人物刻画和复杂的家族关系网络为特 点。': {'冰与火之歌小说系列的主要人物有哪些？': 0.6072996854782104, '冰与火之歌小说系列的故事主线是什么？': 0.5810346007347107, '冰与火之歌小说系列的主要事件是什么？': 0.6145420074462891, '冰与火之歌小说系列的故事背景是什么？': 0.6060986518859863, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5557041764259338, '冰与火之歌小说系列的主题是什么？': 0.5955089330673218, '冰与火之歌小说系列的成功因素有哪些？': 0.5777203440666199, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.5498838424682617, '乔治·R·R·马丁是谁？': 0.23272541165351868}, '冰与火之歌:权谋、荣耀与欲望的恢弘史诗 介绍 《冰与火之歌》是美国作家乔治·R·R·马丁创作的一部史诗奇幻小说系列,被广 泛誉为现代奇幻文学的巅峰之作。该系列小说以中世纪欧洲为背景,具有浓厚 的政治阴谋、荣耀和欲望的元素,引发了全球读者群体的狂热追捧。故事背景 故事发生在虚构的七大王国大陆上。数个封建领主家族和一个暴君共同统治这 片土地。': {'冰与火之歌小说系列的主要人物有哪些？': 0.5277740359306335, '冰与火之歌小说系列的故事主线是什么？': 0.5353829860687256, '冰与火之歌小说系列的主要事件是什么？': 0.5342440605163574, '冰与火之歌小说系列的故事背景是什么？': 0.5584322214126587, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.48513564467430115, '冰与火之歌小说系列的主题是什么？': 0.522860586643219, '冰与火之歌小说系列的成功因素有哪些？': 0.510589599609375, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.47407639026641846, '乔治·R·R·马丁是谁？': 0.2640494108200073}, '3.龙母:作为流亡贵族的最后一名幸存者,她带领三条幼龙逐渐成长,并向 铁王座发起挑战。她是荣耀与欲望的象征之一。情节剧变和复杂关系 1.纷争与叛乱:各个家族、各种势力之间展开了相互争斗、背叛和内讧的故 事情节。读者将跟随主人公们经历暗黑而曲折的命运。': {'冰与火之歌小说系列的主要人物有哪些？': 0.477159708738327, '冰与火之歌小说系列的故事主线是什么？': 0.48683562874794006, '冰与火之歌小说系列的主要事件是什么？': 0.5140298008918762, '冰与火之歌小说系列的故事背景是什么？': 0.479809045791626, '冰与火之歌小说系列的主要情节转折点有哪些？': 0.5342103838920593, '冰与火之歌小说系列的主题是什么？': 0.45075446367263794, '冰与火之歌小说系列的成功因素有哪些？': 0.47802644968032837, '冰与火之歌小说系列对现代奇幻小说的影响是什么？': 0.37755483388900757, '乔治·R·R·马丁是谁？': 0.2073982059955597}}})

    encoded = context_encode(contextaaaaa)
    decoded = context_decode(encoded)
    save_to_es(encoded, 987987, index_name="ai_news_doc_qa")

    data = load_from_es({
        "query": {
            "bool": {
                "must": [
                    {"match": {"session_id": 987987}}
                ]
            }
        },
        "size": 10
    }, es_name="ES_QA", index_name="ai_news_doc_qa")
    decoded_context = context_decode(data)
    print(decoded_context)
