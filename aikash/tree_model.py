import os
import random
import pickle
import datetime
import requests
import json
import time
from dataclasses import dataclass

count_bots = 3

COUNT_CONTEXT_SIZE = 100
TIME_PASSIVE_MINUTE = 30
MAX_SIZE_AI_INPUT_TEXT = 60


_PATH_CHATS = f'{os.getcwd()}/temp/tree'
_URL_MESSAGE = 'http://127.0.0.1:5052/new_bot_message'
_URL_BOT_INFO = 'http://127.0.0.1:5052/bot_info'


def serialize_data(obj, filename):
    directory = _PATH_CHATS
    if not os.path.exists(directory):
        os.makedirs(directory)

    filepath = os.path.join(directory, filename + '.pkl')
    with open(filepath, 'wb') as file:
        pickle.dump(obj, file)


def deserialize_data(filepath):
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'rb') as file:
        obj = pickle.load(file)
    return obj


def compare_strings_by_fragments(str1, str2):
    fragment_length = range(3, 10)
    common_fragments = set()

    for length in fragment_length:
        for i in range(len(str1) - length + 1):
            fragment = str1[i:i + length]
            if fragment in str2:
                common_fragments.add(fragment)

    return len(common_fragments)


def send_post_request(url, data):
    response = requests.post(url, json=data)
    response_json = response.json()

    if 'error' in response_json:
        raise Exception(f"Error: {response_json['error']}")

    return response_json


@dataclass
class Tree:

    def __init__(self, def_response):
        self.tree = {}
        self.def_response = def_response
        self.deserialize_tree()

    def serialize_tree(self):
        for key_chats in self.tree:
            serialize_data(self.tree[key_chats], f"{key_chats}")

    def deserialize_tree(self):
        directory_path = _PATH_CHATS
        if not os.path.isdir(directory_path):
            return

        files = os.listdir(directory_path)
        for file in files:
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                self.tree[os.path.splitext(file_path)[0].split("\\")[-1]] = deserialize_data(file_path)

    def find_context(self, id_chat, id_message=None, id_user=None, date=None):
        self.check_chat_load(id_chat)
        context_list = self.tree[id_chat]
        for iter_mes in reversed(context_list):
            if id_message is None or id_message == iter_mes.id_message:
                if id_user is None or id_user == iter_mes.id_user:
                    if date is None or date == iter_mes.date:
                        return iter_mes
            if date is not None:
                if iter_mes.date < date:
                    return None
        return None

    def check_chat_load(self, id_chat):
        if id_chat not in self.tree:
            des_data = deserialize_data(f'{_PATH_CHATS}/{id_chat}.pkl')
            if des_data is not None:
                self.tree[id_chat] = des_data

        if id_chat not in self.tree:
            self.tree[id_chat] = []

    def work_tree(self):
        for key_chats, sublist in list(self.tree.items()):
            # спонтанный вброс
            if random.random() < 0.15:
                if len(sublist) > 10:
                    context = random.choice(sublist[-8:-3])
                else:
                    context = random.choice(sublist)
                context.work_context(self, self.def_response)

    def clear_tree(self):
        try:
            for key_chats, sublist in list(self.tree.items()):
                if len(sublist) > COUNT_CONTEXT_SIZE:
                    sublist = sublist[-COUNT_CONTEXT_SIZE:-1]
                for iter_con in reversed(sublist):
                    if not iter_con.from_bot:
                        if iter_con.date < int(time.time()) - 60 * TIME_PASSIVE_MINUTE:
                            del self.tree[key_chats]
                        break
                    if iter_con.id_message == sublist[0].id_message:
                        del self.tree[key_chats]
                        break
        except Exception as e:
            self.deserialize_tree()

    def new_context(self,
                    id_chat,
                    id_user,
                    id_message,
                    reply_id_message,
                    from_bot,
                    text_message,
                    date,
                    status=True,
                    reply_context=None):

        self.check_chat_load(id_chat)
        chat = self.tree[id_chat]

        # ищем ссылку
        if reply_id_message is None:
            chat = self.tree[id_chat]
            if len(text_message) < 10:
                if chat[-1].date > int(time.time()) - 20:
                    reply_id_message = chat[-1].id_message
            else:
                io_context = chat[-1]
                io = compare_strings_by_fragments(io_context.text_message, text_message)
                if len(chat) > 10:
                    for iter_con in reversed(chat)[:10]:
                        if compare_strings_by_fragments(iter_con.text_message, text_message) > io:
                            io_context = iter_con
                else:
                    io_context = chat[-1]
                reply_id_message = io_context.id_message

        new_context = Context(id_chat=id_chat,
                              id_user=id_user,
                              id_message=id_message,
                              reply_id_message=reply_id_message,
                              from_bot=from_bot,
                              text_message=text_message,
                              date=date,
                              status=status,
                              reply_context=None)

        if reply_context is None:
            reply_context = self.find_context(id_chat, id_message=reply_id_message)
        if reply_context is not None:
            new_context.reply_context = reply_context

        chat.append(new_context)
        return new_context

    def cycle(self):
        while True:
            print(f"cycle - {time.time()}")
            time.sleep(3)
            try:
                self.serialize_tree()
                self.clear_tree()
                self.work_tree()
            except Exception as e:
                print(f"Exception: {e}")


@dataclass
class Context:
    id_chat: int
    id_user: int
    id_message: int
    reply_id_message: int
    from_bot: bool
    text_message: str
    date: int
    reply_context: all
    status: bool

    # получает цепочку текстового контекста
    def get_context(self, text=""):
        text = f"{text} {self.text_message}"
        if self.reply_context is not None:
            if len(f"{text} {self.reply_context.text_message}") < MAX_SIZE_AI_INPUT_TEXT:
                return self.reply_context.get_context(text=text)
        return text

    # обрабатывает необходимость ответа, в случае истины формирует context
    def work_context(self, tree, def_response):

        # не подтвержден
        if not self.status:
            return

        # определяем нужен ли ответ
        if self.from_bot:
            probability = 1.2 / count_bots
        else:
            probability = 0.6
        if random.random() > probability:
            return

        # определяем user
        def find_user(context, id_user, step=0):
            if context.id_user != id_user and context.from_bot:
                return context.id_user
            elif self.reply_context is not None and step < 3:
                return find_user(context.reply_context, id_user, step + 1)
            else:
                try:
                    res = send_post_request(_URL_BOT_INFO, {'id_chat': context.id_chat})
                    return random.choice(list(res["id_bots"]))
                except:
                    return None

        user = find_user(self, self.id_user)
        if user is None:
            return

        # определяем input_text
        input_text = self.get_context()

        # генерируем ответ
        output_text = def_response(input_text)

        # делаем отправку
        data_context = {
            'id_chat': self.id_chat,
            'message': {
                'user': {
                    'id_user': user
                },
                'text': output_text,
                'reply_to_message_id': self.id_message
            }
        }
        try:
            send_post_request(_URL_MESSAGE, data_context)
        except:
            return

        # формируем context
        context = tree.new_context(id_chat=data_context['id_chat'],
                                   id_user=data_context['message']['user']['id_user'],
                                   id_message=None,
                                   reply_id_message=data_context['message']['reply_to_message_id'],
                                   from_bot=True,
                                   text_message=data_context['message']['text'],
                                   date=None,
                                   status=False)
