import requests
from bs4 import BeautifulSoup
from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine('sqlite:///test', echo=True)


class VkUser(Base):
    __tablename__ = 'vk_users'
    vk_user_id = Column('vk_user_id', Integer, primary_key=True, unique=True)
    fullname = Column('fullname', String)

    def __init__(self, vk_user_id):
        self.vk_user_id = vk_user_id
        self.fullname = self._get_user_name_from_vk_id(vk_user_id)

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
    vk_user_id = Column('vk_user_id', Integer, ForeignKey("vk_users.vk_user_id"), nullable=True),
    name = Column('name', String)

    def __init__(self, name, vk_user_id):
        self.name = name
        self.vk_user_id = vk_user_id

    def __repr__(self):
        return "<Keyword('%s')>" % (self.name)


if __name__ == '__main__':
    # Создание таблицы
    Base.metadata.create_all(engine)
