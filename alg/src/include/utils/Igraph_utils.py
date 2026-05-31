import copy
from collections import deque
import string
import copy
import pickle
import base64
import os
from typing import List
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
import networkx as nx
cur_dir = os.path.dirname(os.path.abspath(__file__))

# 首尾结点类
class VNode(object):
    def __init__(self, val):
        self.val = val  # 存放结点信息
        self.next = []  # 指向下个节点
        self.former = []  # 记录上个节点

    def add_next(self, node):
        self.next.append(node)

    def add_former(self, node):
        self.former.append(node)


# 中间节点类
class ArcNode(VNode):
    def __init__(self, val):
        super().__init__(val=val)
        self.FunctionCall = None
        self.need_rag = False
        self.answer = None

    def add_param(self, attr:str, value:str, attr_type="list"):
        """ 
        输入：
            attr 新增属性名字
            value 新增属性值
            attr_type 只支持list 和 string
        逻辑：
            attr如果存在：
                如果是list，则在原有基础上append新value
                如果是string，替换原有value
            attr如果不存在：
                根据attr_type类型，储存value值。
        """
        
        if hasattr(self, attr):
            ori_value = getattr(self, attr)
            if type(ori_value) == list:
                value = ori_value + [value]
            setattr(self, attr, value)
        else:
            if attr_type == "list":
                setattr(self, attr, [value])
            elif attr_type == "string":
                setattr(self, attr, value)
            else:
                raise ValueError("ArcNode 新添加的属性种类只支持list和string.")


# 图
class IGraph:
    def __init__(self, ):
        """
        有向无环图，信息单向流动最终指向END，每个节点可以有多个上游节点或者多个下游节点。
        """
        self.StartNode = VNode("Start")
        self.EndNode = VNode("End")
        self.StartNode_id = 0
        self.EndNode_id = 1
        self.arcnodes = [self.StartNode, self.EndNode]
        self.is_complex = None
        self.origin_query = ""
        self.rewrite_query = ""
        self.cot_queries_order = []

    def getVNum(self):
        '''返回图中的顶点数'''
        return len(self.arcnodes)

    def __getitem__(self, query):
        """输入query文字，返回对应节点"""
        for node in self.arcnodes:
            if node.val == query:
                return node
        return None

    def print_infostream(self, query, stream: str = "up"):
        """输入query文字，返回对应节点的上游下游问题，默认上游问题，stream输入可选择up/stream"""
        node = None
        for pt in self.arcnodes:
            if pt.val == query:
                node = pt
                break
        stream_lis = pt.former if stream == "up" else pt.next
        if node:
            res = []
            for i in stream_lis:
                res.append(self.arcnodes[i].val)
            return res
        else:
            return None

    # 添加节点，默认在start后面，end前面
    def add_new_node(self, node: ArcNode):
        node.former = [self.StartNode_id]
        node.next = [self.EndNode_id]
        self.arcnodes.append(node)
        node_id = len(self.arcnodes) - 1
        self.EndNode.former.append(node_id)
        self.StartNode.next.append(node_id)

    # 在现有Graph中插入一个节点，在原节点前面
    def insert_node_front(self, new_node, ori_node_val):
        for ori_i in range(len(self.arcnodes)):
            if self.arcnodes[ori_i].val == ori_node_val:
                break
        new_node.former = self.arcnodes[ori_i].former
        new_node.next.append(ori_i)
        self.arcnodes.append(new_node)
        new_node_id = len(self.arcnodes) - 1
        former_lis = self.arcnodes[ori_i].former
        for j in former_lis:
            self.arcnodes[j].next.remove(ori_i)
            self.arcnodes[j].next.append(new_node_id)
        self.arcnodes[ori_i].former = [new_node_id]

    # 在现有Graph中插入一个节点，在原节点后面
    def insert_node_back(self, query, ori_node_val):
        new_node = ArcNode(query)
        for ori_i in range(len(self.arcnodes)):
            if self.arcnodes[ori_i].val == ori_node_val:
                break
        new_node.next = self.arcnodes[ori_i].next
        new_node.former.append(ori_i)
        self.arcnodes.append(new_node)
        new_node_id = len(self.arcnodes) - 1
        next_lis = self.arcnodes[ori_i].next
        for j in next_lis:
            self.arcnodes[j].former.remove(ori_i)
            self.arcnodes[j].former.append(new_node_id)
        self.arcnodes[ori_i].next = [new_node_id]

    # 用于有依赖关系的节点添加，和 insert_node_back 的最大区别就是新加入的节点不打断原有的（非指向END的）箭头指向
    def add_arrow(self, query, former_val):  # C_i 依赖于 B_i
        later_val = query  # 新加节点
        for B_i in range(len(self.arcnodes)):
            if self.arcnodes[B_i].val == former_val:
                break
        C_i = None
        # 非首次添加
        for tmp_i in range(len(self.arcnodes)):
            if self.arcnodes[tmp_i].val == later_val:
                C_i = tmp_i
                break
        # 首次添加
        if C_i == None:
            new_node = ArcNode(later_val)
            self.arcnodes.append(new_node)
            C_i = len(self.arcnodes) - 1

        # 控制上游问题是否不在结果暴露，暂定全部暴露。
        # if self.EndNode_id in self.arcnodes[B_i].next:
        #     self.arcnodes[B_i].next.remove(self.EndNode_id)
        #     self.arcnodes[self.EndNode_id].former.remove(B_i)
        # 加箭头
        self.arcnodes[B_i].next.append(C_i)
        self.arcnodes[C_i].former.append(B_i)
        if self.arcnodes[C_i].next == []:
            self.arcnodes[C_i].next.append(self.EndNode_id)
            self.arcnodes[self.EndNode_id].former.append(C_i)

    # 更新节点的属性
    def update_node_param(self, ori_val, new_val=None, function_call=None, need_rag=None, answer=None):
        for i in range(len(self.arcnodes)):
            if self.arcnodes[i].val == ori_val:
                break
        if new_val:
            self.arcnodes[i].val = new_val
        if function_call:
            self.arcnodes[i].FunctionCall = function_call
        if need_rag:
            self.arcnodes[i].need_rag = need_rag
        if answer:
            self.arcnodes[i].answer = answer
    
    def add_node_param(self, val:str, *args, **kwargs):
        for i in range(len(self.arcnodes)):
            if self.arcnodes[i].val == val:
                break   
        self.arcnodes[i].add_param(*args, **kwargs)
    

    def del_node_param(self, val:str, attr:str):
        for i in range(len(self.arcnodes)):
            if self.arcnodes[i].val == val:
                break   
        if hasattr(self.arcnodes[i], attr):
            delattr(self.arcnodes[i], attr)

    
    #   # BFS 输出解答顺序 可处理多上游情况
    def get_turns(self):
        def check_former_finished(check_ids, finished_ids):
            """ 检查上游问题是否已经被解答了 """
            for id in check_ids:
                if id not in finished_ids:
                    return False
            return True

        finished = [self.StartNode_id]
        queue = [self.StartNode]
        query_turn = []
        while queue != []:
            tmp_queue = []
            tmp_finished = []
            for cur_node in queue:
                for next_id in cur_node.next:
                    # 下游节点不是END，且之前依赖的node已经被解答，则可以记录
                    if next_id != self.EndNode_id and check_former_finished(self.arcnodes[next_id].former, finished):
                        tmp_queue.append(self.arcnodes[next_id])
                        tmp_finished.append(next_id)

            tmp_queue = list(set(tmp_queue))
            queue = tmp_queue
            finished += tmp_finished
            val_turn = [x.val for x in tmp_queue]
            if val_turn != []:
                query_turn.append(val_turn)
        query_turn = [sort_queries_order(each_turn, self.cot_queries_order) for each_turn in query_turn]
        return None, query_turn, None

    # BFS 输出解答顺序 注意：仅仅适用于每个节点只有一个上游问题的情况，否则输出顺序是错误的。
    def get_turns_origin(self):
        final = []
        lis = []
        queue = deque([self.StartNode])
        while queue:
            node = queue.popleft()
            for next_id in node.next:
                if next_id != self.EndNode_id:
                    lis.append(next_id)
                    queue.append(self.arcnodes[next_id])
            if lis:
                final.append(lis)
                lis = []

        node_turn, query_turn = [], []
        for obj in final:
            turn, texts = [], []
            for idx_ in obj:
                turn.append(self.arcnodes[idx_])
                texts.append(self.arcnodes[idx_].val)
            node_turn.append(turn)
            query_turn.append(texts)
        return node_turn, query_turn, final

    # 获取或者打印某属性为True的节点val
    def get_attr(self, attr_name):
        final = []
        for i in range(2, len(self.arcnodes)):
            if getattr(self.arcnodes[i], attr_name):
                final.append(self.arcnodes[i].val)
        return final

    def print_attr(self, attr_name):
        print(f"-------dag图中属性{attr_name}非空非False的有---------")
        for i in range(2, len(self.arcnodes)):
            if getattr(self.arcnodes[i], attr_name):
                print(self.arcnodes[i].val)

    # 打印图中节点关系
    def print_relation(self):
        record_lis = []

        def cur_relation(cur_node):
            if not cur_node:
                cur_node = self.StartNode

            lis = []
            for i in cur_node.next:
                lis.append([cur_node.val, self.arcnodes[i].val])
                if self.arcnodes[i].val != "End" and i not in record_lis:
                    record_lis.append(i)
                    tmp_lis = cur_relation(self.arcnodes[i])
                    lis += tmp_lis
            return lis

        final = cur_relation(self.StartNode)  # 带有Start的所有有边线的节点组合

        for obj in final:
            if "Start" in obj:
                final.remove(obj)  # 不带Start
        # for obj in final:
        #     print(obj)
        return final

    def draw_relations(self, draw_type="spread"):
        """
        绘图表示节点关系，draw_type表示节点分散程度，如果非 spread
        """
        myfont = FontProperties(fname=os.path.join(cur_dir, "STXingkai.ttf"),size=20)  #fname指定字体文件  选简体显示中文
        relations = self.print_relation()   # 获取有向关系  [['A', 'End'], ['A', 'B'], ['B', 'End'], ['B', 'C'], ['C', 'End']]
        lis = []
        relations_num = []
        for obj in relations:
            x, y = obj
            if x not in lis:
                lis.append(x)
            if y not in lis:
                lis.append(y)
        for i in range(len(lis)):
            for j in range(i + 1, len(lis)):
                if [lis[i], lis[j]] in relations:
                    relations_num.append([i, j])
                if [lis[j], lis[i]] in relations:
                    relations_num.append([j, i])
        print_line = ""
        # # 定义图的节点和边
        alphabeta = [chr(id_ + 65) for id_ in range(22)]
        nodes = []
        for id_ in range(len(lis)):
            if lis[id_] != "End":
                fn = alphabeta.pop(0)
                print_line += fn + ": " + lis[id_] + "\n"
                nodes.append(fn)
            else:
                nodes.append("End")
        print(print_line)
        edges = [(nodes[obj[0]], nodes[obj[1]], 1) for obj in relations_num]
        G2 = nx.DiGraph()
        G2.add_nodes_from(nodes)
        G2.add_weighted_edges_from(edges)

        if draw_type == "spread":
            pos2 = nx.circular_layout(G2)
        else:
            pos2 = nx.spring_layout(G2)
        plt.subplot()
        nx.draw(G2, pos2, with_labels=True, font_weight='bold')
        plt.title('示意', fontproperties=myfont)
        # plt.axis('on')
        plt.xticks([])
        plt.yticks([])
        plt.show()

    # 初始化一个几点（非首尾节点）


def init_ArcNode(val):
    return ArcNode(val)


# 序列化并编码
def context_encode(obj: IGraph):
    serialized = pickle.dumps(copy.deepcopy(obj), protocol=pickle.HIGHEST_PROTOCOL)
    return base64.b64encode(serialized).decode("utf-8")


# 解码并反序列化
def context_decode(serialized_str) -> IGraph:
    decoded_bytes = base64.b64decode(serialized_str)
    return pickle.loads(decoded_bytes)


def save_pickle(data, pth):
    file = open(pth, 'wb')
    pickle.dump(data, file)
    file.close()


def load_pickle(pth):
    with open(pth, 'rb') as file:
        data = pickle.load(file)
    return data

def sort_queries_order(raw_queries:List, ref_queries_order:List):
    """
    根据参考的 ref_queries_order 顺序排序，返回排序后的 queries
    """
    if all(element in ref_queries_order for element in raw_queries):
        order_dict = {val: idx for idx, val in enumerate(ref_queries_order)}
        ordered_queries = sorted(raw_queries, key=lambda item: order_dict.get(item, len(ref_queries_order)))
        return ordered_queries
    else:
        return raw_queries


def construct_dag(sub_questions:List, related_records:List = None):
    # 单节点
    if len(sub_questions) == 1:
        dag = IGraph()
        dag.is_complex = False
        node = ArcNode(sub_questions[0]) 
        dag.add_new_node(node)
        return dag
    # 多节点并行
    if not related_records:
        dag = IGraph()
        dag.is_complex = True
        for i, ques in enumerate(sub_questions):
            node = ArcNode(ques) 
            dag.add_new_node(node)
        dag.cot_queries_order = sub_questions  # 并行节点记录顺序
        return dag
    # 多节点串行
    dag = IGraph()
    dag.is_complex = True
    for i, ques in enumerate(sub_questions):
        if related_records[i] == []:
            node = ArcNode(ques) 
            dag.add_new_node(node)
        else:
            while related_records[i]:
                pt = related_records[i].pop(0)
                dag.add_arrow(sub_questions[i], sub_questions[pt])

    return dag


if __name__ == "__main__":
    dag = IGraph()
    x = ArcNode("近几个月政府工作报告的重点内容是什么？")
    x2 = ArcNode("上个月的政府工作报告主要强调了哪些方面？")
    x3 = ArcNode("在促消费方面，政府工作报告提出了哪些具体措施？")
    x2.need_rag = True
    x3.need_rag = True
    dag.add_new_node(x)
    dag.add_new_node(x2)
    dag.add_new_node(x3)
    # res = dag.get_attr("need_rag")
    res = dag.get_turns()
    print(res)
    exit()
    dag.add_arrow("这个天气穿什么衣服？", "1月1日上海，今天天气怎么样？")

    # # 1. 打印有逻辑关系的子问题
    # query_pairs = dag.print_relation()
    # print("===================")

    # # 2. 打印可以并行解答的子问题组。
    # node_turn, query_turn, final = dag.get_turns()
    # print(query_turn)
    # print("===================")

    # # 3. 查看某个问题的相关属性
    # node = dag["这个天气穿什么衣服？"]
    # print(node.FunctionCall)
    # print(node.need_rag)

    # # 4. 查看某个问题的上游或者下游问题
    # # 查看下游
    # downqueries = dag.print_infostream("1月1日上海，今天天气怎么样？", stream="down")
    # print(downqueries)
    # # 查看上游
    # upqueries = dag.print_infostream("1月1日上海，今天天气怎么样？")
    # print(upqueries)

    # ## 检索回答
    # # 5. 将回答的结果储存到dag中
    # dag["这个天气穿什么衣服？"].answer = "军大衣"  # 或者  node.answer = "军大衣"

    # 6. 动态添加属性
    # string 属性储蓄 会更新替换
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽A", attr_type="string")
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽B")
    print(dag["1月1日上海，今天天气怎么样？"].new_attr)
    # 属性删除
    dag.del_node_param("1月1日上海，今天天气怎么样？", "new_attr")
    print(hasattr(dag["1月1日上海，今天天气怎么样？"], "new_attr"))

    # list 属性储蓄 会append
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽A")
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽B")
    print(dag["1月1日上海，今天天气怎么样？"].new_attr)

    # 6. 动态添加属性
    # string 属性储蓄 会更新替换
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽A", attr_type = "string")
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽B")
    print(dag["1月1日上海，今天天气怎么样？"].new_attr)
    # 属性删除
    dag.del_node_param("1月1日上海，今天天气怎么样？", "new_attr")
    print(hasattr(dag["1月1日上海，今天天气怎么样？"], "new_attr"))

    # list 属性储蓄 会append
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽A")
    dag.add_node_param("1月1日上海，今天天气怎么样？", "new_attr", "吗喽B")
    print(dag["1月1日上海，今天天气怎么样？"].new_attr)

    




    # pth = "./dag.pickle"
    # dag = context_decode(load_pickle(pth))
    # dag.draw_relations()