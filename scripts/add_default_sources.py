#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
from app import create_app, db
from app.models import NewsSource

SOURCES = [
    ('知乎日报', 'https://www.zhihu.com/rss/daily', 'RSS', 60),
    ('新浪新闻', 'https://rss.sina.com.cn/sina_all.xml', 'RSS', 30),
    ('澎湃新闻', 'https://www.thepaper.cn/rss/', 'RSS', 30),
    ('果壳网', 'https://www.guokr.com/rss/', 'RSS', 60),
    ('36氪', 'https://36kr.com/feed', 'RSS', 60),
]

app = create_app()
with app.app_context():
    db.create_all()
    count = 0
    for name, url, typ, interval in SOURCES:
        if not NewsSource.query.filter_by(url=url).first():
            db.session.add(NewsSource(name=name, url=url, source_type=typ, crawl_interval=interval))
            count += 1
            print(f'  + {name}')
        else:
            print(f'  已存在: {name}')
    db.session.commit()
    print(f'\n添加了 {count} 个新闻源')
