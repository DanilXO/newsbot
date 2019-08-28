import feedparser
from bs4 import BeautifulSoup


class NewsParser:
    url = 'http://news.google.com/news/search?q='
    meta_params = '&pz=1&cf=all&ned=ca&hl=ru&gl=RU&ceid=RU:ru&topic=w&output=rss'
    query = ''
    spliter = '%20'

    def __init__(self, lang='ru'):
        self.meta_params = '&pz=1&cf=all&ned=ca&hl={}&gl={}&ceid={}:{}&topic=w&output=rss'.format(lang, lang.upper(),
                                                                                                  lang.upper(), lang)

    def get_news(self, keywords):
        self.query = "{}".format("{}".format(self.spliter).join(keywords))
        d = feedparser.parse("{}{}{}".format(self.url, self.query, self.meta_params))
        news = [{"title": entry.title,
                 "description": BeautifulSoup(entry.description, "lxml").text.replace(u'\xa0', u' '),
                 "link": entry.link} for entry in d['entries']]
        # print(news)
        return news

