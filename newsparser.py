import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
from time import mktime


class NewsParser:
    url = 'http://news.google.com/news/rss'
    meta_params = '?hl=ru&gl=RU&ceid=RU:ru'
    query = ''
    spliter = '%20'

    def __init__(self, lang='ru', delta=timedelta(days=1)):
        self.meta_params = '?hl={0}&gl={1}&ceid={2}:{3}'.format(lang, lang.upper(), lang.upper(), lang)
        self.delta = delta

    def news_is_actual(self, value):
        return True if (datetime.now() - self.delta) <= value["published"] <= (datetime.now() + self.delta) else False

    def get_news(self, keywords=None, delta=timedelta(days=3)):
        self.delta = delta
        if keywords:
            if isinstance(keywords, list) or isinstance(keywords, tuple):
                self.query = "{}{}".format('/search?q=', "{}".format(self.spliter).join(keywords))
            else:
                self.query = "{}{}".format('/search?q=', keywords)
            d = feedparser.parse("{}{}{}".format(self.url, self.query, self.meta_params))
        else:
            self.query = "?"
            d = feedparser.parse("{}{}{}".format(self.url, self.query, self.meta_params))
        news = [{"title": entry.title.split(" - ")[0],
                 "published": datetime.fromtimestamp(mktime(entry.published_parsed)),
                 "link": entry.link} for entry in d['entries']]
        return news

