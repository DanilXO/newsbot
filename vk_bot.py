import random
import re
import sys
import time

import vk_api
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from vk_api.longpoll import VkLongPoll, VkEventType

from models import engine, VkUser, Keyword, News, AssociationNewsFromVkUser
from newsparser import NewsParser
import logging

log = logging.getLogger("botlog")


class VkBot:
    _TOKEN = 'c17d1f7ee9825147a6e1a4dfb2cdaf186666ecf15ea25f7f5297348c23321c9195be7a47f3cd50a07c8d2'

    def __init__(self):
        self._SESSION = vk_api.VkApi(token=self._TOKEN)
        with open('keyboard.json', 'r') as kb:
            self.keyboard = kb.read()
        self._ACTIONS = {"ПОДПИСАТЬСЯ": self.subscribe,
                         "ОТПИСАТЬСЯ": self.unsubscribe,
                         "АКТУАЛЬНАЯ_НОВОСТЬ": self.send_users_news,
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
        try:
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
        except Exception as ex:
            self.db_session.rollback()
            log.error(ex)

    def unsubscribe(self, user_id):
        """ Отписаться от новостей """
        try:
            user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
            if user:
                for relation in user.news:
                    self.db_session.delete(relation)
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
        except Exception as ex:
            self.db_session.rollback()
            log.error(ex)

    def get_user_interests(self, user_id):
        """ Получить интересы пользователя """
        user_interests = self.db_session.query(Keyword).filter(Keyword.vk_user.any(VkUser.vk_user_id == user_id)).all()
        if user_interests:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Ваши интересы: {}".format(", ".join([interest.name for interest in user_interests])),
                keyboard=self.keyboard
            )

    def clear_user_interests(self, user_id, send_msg=True):
        user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
        user.keyword = []
        if send_msg:
            self.api.messages.send(
                    user_id=user_id,
                    random_id=random.randint(0, sys.maxsize),
                    message="Ваши интересы чисты как банный лист. Можете проверить отправив 'Мои интересы'",
                    keyboard=self.keyboard
            )

    def set_user_interests(self, user_id, interests):
        """ Задает новые интересы пользователя """
        self.clear_user_interests(user_id, send_msg=False)
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
                    self.db_session.commit()
                except IntegrityError as ex:
                    self.db_session.rollback()
                    log.error(ex)
            else:
                try:
                    self.db_session.add(Keyword(name=keyword, vk_user=[user]))
                    self.db_session.commit()
                    new_keywords.append(keyword)
                except IntegrityError as ex:
                    self.db_session.rollback()
                    log.error(ex)

        self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Вы успешно добавили новые интересы!"
                        "Теперь вы будете получать новостную подборку согласно вашим предпочтениям.",
                keyboard=self.keyboard
            )

    def get_users_news(self, user_id):
        try:
            user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
            keywords = [interest.name for interest in
                        self.db_session.query(Keyword).filter(Keyword.vk_user.any(VkUser.vk_user_id == user_id))]
            news_list = self.news_parser.get_news(keywords)[:1]
            for keyword in keywords:
                news_list += self.news_parser.get_news(keyword)[:1]
            if news_list:
                for news in news_list:
                    news_in_db = self.db_session.query(News).filter_by(title=news['title']).first()
                    if not news_in_db:
                        a = AssociationNewsFromVkUser()
                        a.child = News(**news)
                        user.news.append(a)
                        self.db_session.add(a)
                        self.db_session.commit()
        except Exception as ex:
            self.db_session.rollback()
            log.error(ex)

    def send_users_news(self, user_id):
        self.api.messages.send(
            user_id=user_id,
            random_id=random.randint(0, sys.maxsize),
            message="Секундочку! Ведется поиск по Вашим интересам.",
            keyboard=self.keyboard
        )
        self.get_users_news(user_id)
        news = self.db_session.query(News).filter(News.vk_user.any(VkUser.vk_user_id == user_id), News.was_readed == False).first()
        if news:
            try:
                news.was_readed = True
                self.db_session.add(news)
                self.db_session.commit()
                self.api.messages.send(
                        user_id=user_id,
                        random_id=random.randint(0, sys.maxsize),
                        message="Новость: {} \nПодробне: {}\n".format(news.title, news.link),
                        keyboard=self.keyboard
                     )
            except:
                self.db_session.rollback()
                self.api.messages.send(
                    user_id=user_id,
                    random_id=random.randint(0, sys.maxsize),
                    message="Для Вас не нашлось актуальных новостей. Будем держать Вас в курсе.",
                    keyboard=self.keyboard
                )
        else:
            self.api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, sys.maxsize),
                message="Для Вас не нашлось актуальных новостей. Будем держать Вас в курсе.",
                keyboard=self.keyboard
            )

    def send_news_for_many_users(self, users_ids, keyword=None):
        try:
            if keyword:
                list_news = self.news_parser.get_news(keyword)
            else:
                list_news = self.news_parser.get_news()
            if list_news:
                return
            news = list_news[0]
            users_was_read_it = self.db_session.query(VkUser.vk_user_id).filter(VkUser.vk_user_id.in_(users_ids),
                                                                                 VkUser.news.any(News.title == news['title']),
                                                                                    VkUser.news.any(News.was_readed == True)).all()

            users_ids = list(set(users_ids) - set([_[0] for _ in users_was_read_it]))
            users = self.db_session.query(VkUser).filter(VkUser.vk_user_id.in_(users_ids)).all()
            for user in users:
                news_in_db = self.db_session.query(News).filter(News.title == news['title']).first()
                with self.db_session.no_autoflush:
                    a = AssociationNewsFromVkUser()
                    if not news_in_db:
                        new_news = News(**news)
                        a.child = new_news
                        a.child.was_readed = True
                        user.news.append(a)
                        self.db_session.commit()
                    elif news_in_db and not self.db_session.query(AssociationNewsFromVkUser)\
                            .filter(AssociationNewsFromVkUser.child == news_in_db, AssociationNewsFromVkUser.parent == user).first():
                        a.child = news_in_db
                        a.child.was_readed = True
                        user.news.append(a)
                        self.db_session.commit()
            if users_ids:
                self.api.messages.send(
                    user_ids=users_ids,
                    random_id=random.randint(0, sys.maxsize),
                    message="Новость: {} \nПодробне: {}\n".format(news["title"], news["link"]),
                    keyboard=self.keyboard
                )
                self.db_session.commit()
        except Exception as ex:
            self.db_session.rollback()
            log.error(ex)

    def _connect(self):
        try:
            self._SESSION.auth(token_only=True)
        except vk_api.AuthError as ex:
            log.error(ex)

    def _eventloop(self, longpoll):
        previous_command = None
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                    comand = event.text.upper().replace(' ', '_')

                    if comand in self._COMANDS:
                        user = self.db_session.query(VkUser).filter_by(vk_user_id=event.user_id).first()
                        if not user and comand in self._COMANDS[1:]:
                            self.api.messages.send(
                                user_id=event.user_id,
                                random_id=random.randint(0, sys.maxsize),
                                message="Сначала необходимо подписатья. Отправьте: 'Подписаться'",
                                keyboard=self.keyboard
                            )
                        elif comand in self._COMANDS[:5]:
                            self._ACTIONS[comand](event.user_id)
                            time.sleep(1)
                        elif comand in self._COMANDS[5:]:
                            previous_command = comand
                            self.api.messages.send(
                                user_id=event.user_id,
                                random_id=random.randint(0, sys.maxsize),
                                message="Перечислите интересующие вас тематики. "
                                        "Например: Apple, Android, Политика",
                                keyboard=self.keyboard
                            )
                            time.sleep(1)
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

    def gen_api(self):
        self._connect()
        longpoll = VkLongPoll(self._SESSION)
        self.api = self._SESSION.get_api()
        return longpoll

    def run(self):
        longpoll = self.gen_api()
        self._eventloop(longpoll)