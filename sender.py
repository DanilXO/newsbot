import time
from sqlalchemy.orm import sessionmaker

from models import engine, VkUser, Keyword
from vk_bot import VkBot

db_session = sessionmaker(bind=engine)()
vk_bot = VkBot()
vk_bot.gen_api()

while True:
    keywords = [interest.name for interest in db_session.query(Keyword).all()]
    if keywords:
        for keyword in keywords:
            users_with_that_keyword = db_session.query(VkUser.vk_user_id).filter(VkUser.keyword.any(name=keyword)).all()
            vk_bot.send_news_for_many_users([_.vk_user_id for _ in users_with_that_keyword], keyword)
    time.sleep(5)