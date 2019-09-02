import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy import Column, Integer, String, create_engine, ForeignKey, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

Base = declarative_base()
engine = create_engine('sqlite:///test.sqlite', echo=True)
# engine = create_engine('sqlite:///test.sqlite', echo=False)


association_vkuser_keywords_table = Table('vkuser_keywords', Base.metadata,
                                          Column('vk_user_id', Integer, ForeignKey('vk_users.vk_user_id')),
                                          Column('keyword_id', Integer, ForeignKey('keywords.id'))
                                          )


class VkUser(Base):
    __tablename__ = 'vk_users'
    vk_user_id = Column('vk_user_id', Integer, primary_key=True, unique=True)
    fullname = Column('fullname', String)
    keyword = relationship(
        "Keyword",
        secondary=association_vkuser_keywords_table,
        back_populates="vk_user")
    news = relationship("News", back_populates="vk_user")

    def __init__(self, vk_user_id, keyword=None):
        self.vk_user_id = vk_user_id
        self.fullname = self._get_user_name_from_vk_id(vk_user_id)
        if keyword is None:
            self.keyword = []
        else:
            self.keyword = keyword

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

    def __repr__(self):
        return "<VkUser('%s','%s')>" % (self.vk_user_id, self.fullname)


class TelegramUser(Base):
    __tablename__ = 'telegram_user'
    telegram_id = Column('telegram_id', Integer, primary_key=True, unique=True)
    fullname = Column('fullname', String)

    def __init__(self, name, fullname, password):
        self.name = name
        self.fullname = fullname

    def __repr__(self):
        return "<TelegramUser('%s','%s')>" % (self.telegram_id, self.fullname)


class Keyword(Base):
    __tablename__ = 'keywords'
    id = Column('id', Integer, primary_key=True, autoincrement=True, unique=True)
    name = Column('name', String, unique=True)

    vk_user = relationship(
        "VkUser",
        secondary=association_vkuser_keywords_table,
        back_populates="keyword")

    def __init__(self, name, vk_user):
        self.name = name
        self.vk_user = vk_user

    def __repr__(self):
        return "<Keyword('%s')>" % (self.name)


class News(Base):
    __tablename__ = 'news'
    id = Column('id', String, primary_key=True, unique=True)
    title = Column('title', String)
    description = Column('description', String)
    published = Column('published', DateTime, default=datetime.datetime.utcnow)
    link = Column('link', String)
    vk_user_id = Column(Integer, ForeignKey('vk_users.vk_user_id'))
    vk_user = relationship("VkUser", back_populates="news")

    def __init__(self, vk_user, id, title, description, published, link):
        self.vk_user = vk_user
        self.vk_user_id = vk_user.vk_user_id
        self.id = id
        self.title = title
        self.description = description
        self.published = published
        self.link = link

    def __repr__(self):
        return "<News('%s')>" % (self.title)


if __name__ == '__main__':
    # Создание таблицы
    Base.metadata.create_all(engine)
