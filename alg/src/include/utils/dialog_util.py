from include.logger import log


class Dialogue:
    def __init__(self):
        self.conversations = []

    def add_conversation(self, role, content):
        self.conversations.append({"role": role, "content": content})

    def get_conversations(self):
        return self.conversations

    def print_conversations(self):
        res = ""
        for conv_iter, conv in enumerate(self.conversations):
            res += ("*"*30)
            res += ("conv_iter: {}\n".format(conv_iter))
            res += ("role: {}\n".format(conv['role']))
            res += ("content: {}\n".format(conv['content']))
        return res


def get_chat_query(query: Dialogue, template, add_template=True):
    template_assistant = "{}<|im_end|>\n<|im_start|>user\n"
    template_user = "{}<|im_end|>\n<|im_start|>assistant\n"
    if add_template:
        conversation = query.get_conversations()
        res_query = ""
        for i, role_i in enumerate(conversation):
            if i == 0:
                res_query += template.format(role_i['content'])
            elif role_i['role'] == 'user':
                res_query += template_user.format(role_i['content'])
            elif role_i['role'] == 'assistant':
                res_query += template_assistant.format(role_i['content'])
        return res_query
    else:
        raise NotImplementedError


if __name__ == '__main__':
    dialog = Dialogue()
    dialog.add_conversation("user", "给我讲个故事")
    dialog.add_conversation("assistant", "从前有个山，山里有个庙，庙里有个小猴子在睡觉")
    dialog.add_conversation("user", "此时来了一只蓝色魔法小和尚，然后，")
    query = get_chat_query(
        dialog,
        template="<|im_start|>system\n"
                 "You are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n")
    print(query)

