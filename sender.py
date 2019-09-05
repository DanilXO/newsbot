import time

import vk_api
from sqlalchemy.orm import sessionmaker

from models import engine, VkUser, Keyword
from vk_bot import VkBot
from datetime import datetime, timedelta

db_session = sessionmaker(bind=engine)()
vk_bot = VkBot()
vk_bot.gen_api()

while True:
    pass
    # # user = self.db_session.query(VkUser).filter_by(vk_user_id=user_id).first()
    keywords = [interest.name for interest in db_session.query(Keyword).all()]
    for keyword in keywords:
        print(keyword)
        users_with_that_keyword = db_session.query(VkUser.vk_user_id).filter(VkUser.keyword.any(name=keyword)).all()
        vk_bot.send_news_for_many_users([_.vk_user_id for _ in users_with_that_keyword], keyword)
    users_without_keyword = db_session.query(VkUser).filter(~VkUser.keyword.any()).all()
    vk_bot.send_news_for_many_users([_.vk_user_id for _ in users_without_keyword])
    # # # time.sleep(2)