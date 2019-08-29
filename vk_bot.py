import random
import re
import sys

import requests
import vk_api
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from vk_api.longpoll import VkLongPoll, VkEventType

from models import engine, VkUser
from newsparser import NewsParser


class VkBot:
    _TOKEN = 'c17d1f7ee9825147a6e1a4dfb2cdaf186666ecf15ea25f7f5297348c23321c9195be7a47f3cd50a07c8d2'

    def __init__(self):
        self._SESSION = vk_api.VkApi(token=self._TOKEN)
        with open('keyboard.json', 'r') as kb:
            self.keyboard = kb.read()
        self._ACTIONS = {"ПОДПИСАТЬСЯ": self.subscribe,
                         "ОТПИСАТЬСЯ": self.unsubscribe,
                         "ПОПУЛЯРНОЕ": self.get_popular_news,
                         "МОИ_ИНТЕРЕСЫ": self.get_user_interests,
                         "ЗАДАТЬ_НОВЫЕ_ИНТЕРЕСЫ": self.set_user_interests,
                         "ДОБАВИТЬ_ИНТЕРЕС": self.add_user_interest,
                         }
        self._COMANDS = list(self._ACTIONS.keys())
        self.db_session = sessionmaker(bind=engine)()
        self.api = None
        self.news_parser = NewsParser(lang='ru')

    def subscribe(self, user_id):
        """ Подписаться на новости """
        if self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first():
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы и так уже подписаны на новостную рассылку.",
                keyboard=self.keyboard
            )
        else:
            new_user = VkUser(user_id)
            self.db_session.add(new_user)
            self.db_session.commit()
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы были успешно подписаны на новости! Задайте свои интересы, "
                        "чтобы получать новости только по определенным тематикам.",
                keyboard=self.keyboard
            )

    def unsubscribe(self, user_id):
        """ Отписаться от новостей """
        user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
        if user:
            self.db_session.delete(user)
            self.db_session.commit()
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы успешно отписались",
                keyboard=self.keyboard
            )

        else:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы ещё не подписались на новостную рассылку.",
                keyboard=self.keyboard
            )

    def get_user_interests(self, user_id):
        """ Получить интересы пользователя """
        if self.USERS_INTERESTS.get(user_id, None) is not None:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Ваши интересы: {}".format(", ".join(self.USERS_INTERESTS.get(user_id))),
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
        self.USERS_INTERESTS[user_id] = re.findall(r"[\w']+", interests)
        self.api.messages.send(
            user_id=user_id,
            random_id=random.randint(0, sys.maxsize),
            message="Вы успешно добавили новые интересы! "
                    "Теперь вы будете получать новостную подборку согласно вашим предпочтениям.",
            keyboard=self.keyboard
        )

    def add_user_interest(self, user_id, interests):
        """ Добавляет новый интерес пользователя """
        if self.USERS_INTERESTS.get(user_id, None):
            self.USERS_INTERESTS[user_id].append(re.findall(r"[\w']+", interests))
        else:
            self.USERS_INTERESTS[user_id] = re.findall(r"[\w']+", interests)
        self.api.messages.send(
            user_id=user_id,
            random_id=random.randint(0, sys.maxsize),
            message="Вы успешно добавили новые интересы! "
                    "Теперь вы будете получать новостную подборку согласно вашим предпочтениям.",
            keyboard=self.keyboard
        )

    def get_popular_news(self, user_id):
        # if self.USERS_INTERESTS.get(user_id):
        #     news_list = self.news_parser.get_news(self.USERS_INTERESTS.get(user_id))[:2]
        # else:
        #     news_list = self.news_parser.get_news([])[:2]
        news_list = self.news_parser.get_news(["Apple", "Android"])[:3]
        if not news_list:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Ничего не найдено. Будем держать вас в курсе...",
                keyboard=self.keyboard
            )
        else:
            row_spliter = "".join("_" for i in range(65))
            for new in news_list:
                self.api.messages.send(
                    user_id=user_id,
                    random_id=random.randint(0, sys.maxsize),
                    message="Новость:\n_________\n❗{}❗\n\n{}\nПодробне:{}\n\n\n".format(new["title"], new["description"],
                                                                                 new["link"]),
                    keyboard=self.keyboard
                )

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
                    comand = event.text.upper().replace(' ', '_')

                    if comand in self._COMANDS:
                        if comand in self._COMANDS[:4]:
                            self._ACTIONS[comand](event.user_id)
                        elif comand in self._COMANDS[4:]:
                            previous_command = comand
                            self.api.messages.send(
                                user_id=event.user_id,
                                random_id=random.randint(0, sys.maxsize),
                                message="Перечислите интересующие вас тематики. "
                                        "Например: Apple, Android, Политика",
                                keyboard=self.keyboard
                            )
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


# class VkUser:
#     """ Класс, представляющий отдельного юзера, подписавшегося на наши обновления """
#
#     def __init__(self, user_id):
#         self.USER_ID = user_id
#         self._USERNAME = self._get_user_name_from_vk_id(user_id)
#
#     def _get_user_name_from_vk_id(self, user_id):
#         request = requests.get("https://vk.com/id" + str(user_id))
#         bs = BeautifulSoup(request.text, "html.parser")
#
#         user_name = self._clean_all_tag_from_str(bs.findAll("title")[0])
#
#         return user_name.split()[0]
#
#     @staticmethod
#     def _clean_all_tag_from_str(string_line):
#         """
#         Очистка строки stringLine от тэгов и их содержимых
#         :param string_line: Очищаемая строка
#         :return: очищенная строка
#         """
#         soup = BeautifulSoup(string_line)
#         return soup.get_text()
