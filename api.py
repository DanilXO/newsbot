from newsparser import NewsParser

keywords = ['Apple', 'Android']

news_parser = NewsParser(lang='ru')
news = news_parser.get_news(keywords)
for new in news:
    print(new)