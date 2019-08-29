import random
import sys

import requests
import vk_api
from bs4 import BeautifulSoup
from vk_api.longpoll import VkLongPoll, VkEventType


class VkBot:
    _TOKEN = 'c17d1f7ee9825147a6e1a4dfb2cdaf186666ecf15ea25f7f5297348c23321c9195be7a47f3cd50a07c8d2'

    def __init__(self):
        self._SESSION = vk_api.VkApi(token=self._TOKEN)
        with open('keyboard.json', 'r') as kb:
            self.keyboard = kb.read()
        self._COMMANDS = ["ПОДПИСАТЬСЯ", "ОТПИСАТЬСЯ", "МОИ_ИНТЕРЕСЫ", "ЗАДАТЬ_НОВЫЕ_ИНТЕРЕСЫ", "ДОБАВИТЬ_ИНТЕРЕС"]
        self._ACTIONS = {"ПОДПИСАТЬСЯ": self.subscribe,
                         "ОТПИСАТЬСЯ": self.unsubscribe,
                         "МОИ_ИНТЕРЕСЫ": self.get_user_interests,
                         "ЗАДАТЬ_НОВЫЕ_ИНТЕРЕСЫ": self.set_user_interests,
                         "ДОБАВИТЬ_ИНТЕРЕС": self.add_user_interest,
                         }
        self.USERS = []
        self.USERS_INTERESTS = {}
        self.api = None

    def subscribe(self, user_id):
        """ Подписаться на новости """
        if user_id in self.USERS:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы и так уже подписаны на новостную рассылку.",
                keyboard=self.keyboard
            )
        else:
            self.USERS.append(user_id)
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы были успешно подписаны на новости! Задайте свои интересы, "
                        "чтобы получать новости только по определенным тематикам.",
                keyboard=self.keyboard
            )

    def unsubscribe(self, user_id):
        """ Отписаться от новостей """
        if user_id not in self.USERS:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы ещё не подписались на новостную рассылку.",
                keyboard=self.keyboard
            )
        else:
            self.USERS.remove(user_id)
            self.USERS_INTERESTS.pop(user_id, None)
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы успешно отписались",
                keyboard=self.keyboard
            )

    def get_user_interests(self, user_id):
        """ Получить интересы пользователя """
        if self.USERS_INTERESTS.get(user_id) is not None:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message=f"Ваши интересы: {self.USERS_INTERESTS.get(user_id)}",
                keyboard=self.keyboard
            )
        else:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы ещё не задали свои интересы и подписаны на общую новостную рассылку.",
                keyboard=self.keyboard
            )

    def set_user_interests(self, user_id, interests):
        """ Задает новые интересы пользователя """
        self.USERS_INTERESTS[user_id] = interests

    def add_user_interest(self, user_id, interests):
        """ Добавляет новый интерес пользователя """
        if self.USERS_INTERESTS[user_id]:
            self.USERS_INTERESTS[user_id] = self.USERS_INTERESTS[user_id] + ", " + interests
        else:
            self.USERS_INTERESTS[user_id] = interests

    def _connect(self):
        try:
            self._SESSION.auth(token_only=True)
        except vk_api.AuthError as error_msg:
            print(error_msg)

    def _eventloop(self, longpoll):
        previous_command = None
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                    command = event.text.upper().replace(' ', '_')

                    if command in self._COMMANDS:
                        if command in self._COMMANDS[:3]:
                            self._ACTIONS[command](event.user_id)
                        elif command in self._COMMANDS[3:]:
                            previous_command = command
                    elif previous_command is not None:
                        self._ACTIONS[previous_command](event.user_id, event.text)
                        previous_command = None
                    else:
                        self.api.messages.send(
                            user_id=event.user_id,
                            random_id=random.randint(0, sys.maxsize),
                            message="Не понимаю о чем Вы...",
                            keyboard=self.keyboard
                        )

    def run(self):
        self._connect()
        longpoll = VkLongPoll(self._SESSION)
        self.api = self._SESSION.get_api()
        print("Server started")
        self._eventloop(longpoll)


class VkUser:
    """ Класс, представляющий отдельного юзера, подписавшегося на наши обновления """

    def __init__(self, user_id):
        self.USER_ID = user_id
        self._USERNAME = self._get_user_name_from_vk_id(user_id)

    def _get_user_name_from_vk_id(self, user_id):
        request = requests.get("https://vk.com/id" + str(user_id))
        bs = BeautifulSoup(request.text, "html.parser")

        user_name = self._clean_all_tag_from_str(bs.findAll("title")[0])

        return user_name.split()[0]

    @staticmethod
    def _clean_all_tag_from_str(string_line):
        """
        Очистка строки stringLine от тэгов и их содержимых
        :param string_line: Очищаемая строка
        :return: очищенная строка
        """
        result = ""
        not_skip = True
        for i in list(string_line):
            if not_skip:
                if i == "<":
                    not_skip = False
                else:
                    result += i
            else:
                if i == ">":
                    not_skip = True
        return result
