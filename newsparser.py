import urllib.parse

import feedparser
from datetime import datetime, timedelta
from time import mktime


class NewsParser:
    url = 'http://news.google.com/news/rss'
    meta_params = '?hl=ru&gl=RU&ceid=RU:ru/'
    query = ''
    spliter = '%20'

    def __init__(self, lang='ru', delta=timedelta(days=3)):
        self.meta_params = '&hl={0}&gl={1}&ceid={2}:{3}'.format(lang, lang.upper(), lang.upper(), lang)
        self.delta = delta

    def news_is_actual(self, value):
        return True if (datetime.now() - self.delta) <= value["published"] <= (datetime.now() + self.delta) else False

    def get_news(self, keywords=None, delta=timedelta(days=3)):
        self.delta = delta
        if keywords:
            if isinstance(keywords, list) or isinstance(keywords, tuple):
                keywords = [urllib.parse.quote(k) for k in keywords]
                self.query = "{}{}".format('/search?q=', "{}".format(self.spliter).join(keywords))
            else:
                self.query = "{}{}".format('/search?q=', urllib.parse.quote(keywords))
            link = "{}{}{}".format(self.url, self.query, self.meta_params)
            d = feedparser.parse(link)
        else:
            link = "{}{}".format(self.url, self.meta_params)
            d = feedparser.parse(link)
        news = [{"title": entry.title.split(" - ")[0],
                 "published": datetime.fromtimestamp(mktime(entry.published_parsed)),
                 "link": entry.link} for entry in d['entries']]
        news = list(filter(self.news_is_actual, news))
        return news

