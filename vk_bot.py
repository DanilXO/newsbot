import random
import re
import sys
import vk_api
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from vk_api.longpoll import VkLongPoll, VkEventType

from models import engine, VkUser, Keyword, News
from newsparser import NewsParser


class VkBot:
    _TOKEN = 'c17d1f7ee9825147a6e1a4dfb2cdaf186666ecf15ea25f7f5297348c23321c9195be7a47f3cd50a07c8d2'

    def __init__(self):
        self._SESSION = vk_api.VkApi(token=self._TOKEN)
        with open('keyboard.json', 'r') as kb:
            self.keyboard = kb.read()
        self._ACTIONS = {"ПОДПИСАТЬСЯ": self.subscribe,
                         "ОТПИСАТЬСЯ": self.unsubscribe,
                         "АКТУАЛЬНАЯ_НОВОСТЬ": self.get_users_news,
                         "ОЧИСТИТЬ_МОИ_ИНТЕРЕСЫ": self.clear_user_interests,
                         "МОИ_ИНТЕРЕСЫ": self.get_user_interests,
                         "ЗАДАТЬ_НОВЫЕ_ИНТЕРЕСЫ": self.set_user_interests,
                         "ДОБАВИТЬ_ИНТЕРЕСЫ": self.add_user_interest,
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
            new_user = VkUser(vk_user_id=user_id)
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
                message="Вы успешно отписались. Очень жаль, мы будем скучать!",
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
        user_interests = self.db_session.query(Keyword).filter(Keyword.vk_user.any(VkUser.vk_user_id == user_id)).all()
        print(user_interests)
        if user_interests:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Ваши интересы: {}".format(", ".join([interest.name for interest in user_interests])),
                keyboard=self.keyboard
            )
        else:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы ещё не задали свои интересы и подписаны на общую новостную рассылку.",
                keyboard=self.keyboard
            )

    def clear_user_interests(self, user_id):
        self.db_session.query(Keyword).filter(Keyword.vk_user.any(VkUser.vk_user_id == user_id))\
                                                                  .delete(synchronize_session='fetch')
        self.db_session.commit()

    def set_user_interests(self, user_id, interests):
        """ Задает новые интересы пользователя """
        self.clear_user_interests(user_id)
        self.add_user_interest(user_id, interests)

    def add_user_interest(self, user_id, interests):
        """ Добавляет новые интересы пользователя """
        user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
        new_keywords = []
        for keyword in re.findall(r"[\w']+", interests):
            keyword = keyword.title()
            exists_kw = self.db_session.query(Keyword).filter_by(name=keyword).first()
            if exists_kw is not None:
                try:
                    exists_kw.vk_user.append(user)
                except IntegrityError:
                    pass
            else:
                try:
                    self.db_session.add(Keyword(name=keyword, vk_user=[user]))
                    self.db_session.commit()
                    new_keywords.append(keyword)
                except IntegrityError:
                    pass
            print(new_keywords)
        if not new_keywords:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Интересы либо заданны не корректно, либо вы уже на них подписаны.",
                keyboard=self.keyboard
            )
        else:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы успешно добавили новые интересы!"
                        "Теперь вы будете получать новостную подборку согласно вашим предпочтениям.",
                keyboard=self.keyboard
            )

    def get_users_news(self, user_id):
        new_news = 0
        user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
        keywords = [interest.name for interest in
                    self.db_session.query(Keyword).filter(Keyword.vk_user.any(VkUser.vk_user_id == user_id))]
        news_list = self.news_parser.get_news(keywords)
        for keyword in keywords:
            news_list += self.news_parser.get_news(keyword)
        if not news_list:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Ничего не найдено. Будем держать вас в курсе...",
                keyboard=self.keyboard
            )
            return
        else:
            readed_news_list = [val.id for val in self.db_session.query(News).filter(News.vk_user.has(VkUser.vk_user_id == user_id))]
            for new in news_list:
                if new['id'] not in readed_news_list:
                    self.api.messages.send(
                        user_id=user_id,
                        random_id=random.randint(0, sys.maxsize),
                        message="Новость:\n_________\n❗{}❗\n\n{}\nПодробне:{}\n\n\n".format(new["title"],
                                                                                            new["description"],
                                                                                            new["link"]),
                        keyboard=self.keyboard
                    )
                    self.db_session.add(News(vk_user=user, **new))
                    self.db_session.commit()
                    new_news += 1
                    return
        if new_news == 0:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Ничего не найдено. Будем держать вас в курсе...",
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
                        if comand in self._COMANDS[:5]:
                            self._ACTIONS[comand](event.user_id)
                        elif comand in self._COMANDS[5:]:
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