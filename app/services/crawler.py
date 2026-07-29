import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app.models import NewsArticle, db


class BaseCrawler:
    
    def __init__(self, source):
        self.source = source
        self.timeout = 30
        self.retry = 3
    
    def fetch(self, url):
        """带重试的请求"""
        for i in range(self.retry):
            try:
                resp = requests.get(url, timeout=self.timeout, headers={
                    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                   'Chrome/120.0.0.0 Safari/537.36')
                })
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                if i == self.retry - 1:
                    raise e
        return None
    
    def parse(self, html):
        """子类重写解析方法"""
        raise NotImplementedError
    
    def run(self):
        """采集入口"""
        html = self.fetch(self.source.url)
        if not html:
            return []
        articles = self.parse(html)
        return self.save_articles(articles)
    
    def save_articles(self, articles_data):
        """保存文章，自动去重，根据标题关键词自动分类"""
        import re
        _cy = __import__('datetime').datetime.now().year
        saved = []
        for data in articles_data:
            _t = (data.get('title') or '') + ' ' + (data.get('content') or '')
            _ys = re.findall(r'20\d{2}', _t)
            if _ys and min(int(y) for y in _ys) < _cy - 1:
                continue
            existing = NewsArticle.query.filter_by(url=data.get('url')).first()
            if existing:
                continue
            cat = '综合'
            t = _t
            if any(k in t for k in ['考研','考公','公务员','行测','招生','研究生','复试','考点','备考','录取','分数线','国考','省考','申论','事业单位','教师招聘']):
                cat = '考公考研'
            elif any(k in t for k in ['招聘','求职','简历','就业','实习','校招','管培生','应届生','秋招','春招']):
                cat = '应届求职'
            elif any(k in t for k in ['股票','股市','大盘','涨停','跌停','上证','深证','创业板','科创板','恒生','A股','港股','美股','基金','ETF','牛市','熊市','涨幅','跌幅','成交额','板块','指数','开盘','收盘','投资','估值','行情','回调','反弹','仓位','持仓']):
                cat = '股票市场'
            article = NewsArticle(
                category=cat,
                title=data.get('title'),
                content=data.get('content'),
                publish_time=data.get('publish_time'),
                author=data.get('author'),
                source_site=self.source.name,
                url=data.get('url'),
                source_id=self.source.id
            )
            db.session.add(article)
            saved.append(article)
        db.session.commit()
        # 限制总文章数不超过100篇，超出时删除最旧的
        # 限制总文章数，超出时删除最旧的（新文章自动替代旧文章）
        _MAX_ARTICLES = 500
        total = NewsArticle.query.count()
        if total > _MAX_ARTICLES:
            exceed = total - _MAX_ARTICLES
            oldest = NewsArticle.query.order_by(NewsArticle.collected_at.asc()).limit(exceed).all()
            for o in oldest:
                db.session.delete(o)
            db.session.commit()
        return saved


class ExampleNewsCrawler(BaseCrawler):
    """示例爬虫：针对特定新闻网站的解析"""
    
    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        for item in soup.select('.news-item'):
            title_el = item.select_one('.title')
            link_el = item.select_one('a')
            time_el = item.select_one('.time')
            if not title_el or not link_el:
                continue
            articles.append({
                'title': title_el.text.strip(),
                'url': link_el['href'],
                'publish_time': datetime.now(),  # 实际需解析时间字符串
                'content': '...'  # 实际可能需再请求详情页
            })
        return articles


class CrawlerFactory:
    """爬虫工厂：根据新闻源类型返回对应爬虫实例"""
    
    @staticmethod
    def get_crawler(source):
        if source.source_type == 'RSS':
            return RssCrawler(source)
        elif source.source_type == 'API':
            return ApiCrawler(source)
        else:
            return ExampleNewsCrawler(source)


class RssCrawler(BaseCrawler):
    """RSS Feed 解析爬虫（使用 feedparser）"""
    
    def parse(self, html):
        import feedparser
        feed = feedparser.parse(html)
        articles = []
        for entry in feed.entries:
            pub_time = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                from time import mktime
                pub_time = datetime.fromtimestamp(mktime(entry.published_parsed))
            articles.append({
                'title': entry.get('title', ''),
                'url': entry.get('link', ''),
                'publish_time': pub_time or datetime.now(),
                'author': entry.get('author', ''),
                'content': entry.get('description', entry.get('summary', ''))
            })
        return articles


class ApiCrawler(BaseCrawler):
    """API 源爬虫：预期返回 JSON 格式"""
    
    def parse(self, html):
        import json
        try:
            data = json.loads(html)
            articles = []
            items = data.get('items', data.get('data', []))
            for item in items:
                articles.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'publish_time': datetime.now(),
                    'content': item.get('content', item.get('description', ''))
                })
            return articles
        except json.JSONDecodeError:
            raise ValueError('API 返回的不是合法 JSON')
