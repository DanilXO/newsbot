import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
from time import mktime


class NewsParser:
    url = 'http://news.google.com/news/'
    meta_params = '&pz=1&cf=all&ned=ca&hl=ru&gl=RU&ceid=RU:ru&topic=w&output=rss'
    query = ''
    spliter = '%20'

    def __init__(self, lang='ru'):
        self.meta_params = '&pz=1&cf=all&ned=ca&hl={}&gl={}&ceid={}:{}&topic=w&output=rss'.format(lang, lang.upper(),
                                                                                                  lang.upper(), lang)

    def news_is_actual(self, value):
        return True if (datetime.now() - timedelta(days=1)) <= value["published"] <= (datetime.now() + timedelta(days=1)) else False

    def get_news(self, keywords=None):
        if keywords:
            self.query = "{}{}".format('search?q=', "{}".format(self.spliter).join(keywords))
        else:
            self.query = "?"
        d = feedparser.parse("{}{}{}".format(self.url, self.query, self.meta_params))
        news = [{"id": entry.id,
                 "title": entry.title,
                 "description": BeautifulSoup(entry.description, "lxml").text.replace(u'\xa0', u' '),
                 "published": datetime.fromtimestamp(mktime(entry.published_parsed)),
                 "link": entry.link} for entry in d['entries']]
        print(news)
        news = list(filter(self.news_is_actual, news))
        return news

