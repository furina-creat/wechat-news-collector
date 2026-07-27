import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db

app = create_app()

# 确保启动时创建表
with app.app_context():
    try:
        db.create_all()
        print("✅ 数据库已就绪")
        # 首次启动生成种子数据
        from app.models import NewsArticle, NewsSource, db as _db
        if NewsSource.query.count() == 0:
            # 种子源
            sources = [
                ("36氪", "https://36kr.com/feed", "RSS", 60),
                ("澎湃新闻", "https://www.thepaper.cn/rss/", "RSS", 60),
                ("知乎日报", "https://www.zhihu.com/rss/daily", "RSS", 60),
                ("新浪新闻", "https://rss.sina.com.cn/sina_all.xml", "RSS", 60),
            ]
            for name, url, st, interval in sources:
                _db.session.add(NewsSource(name=name, url=url, source_type=st, crawl_interval=interval, category='综合'))
            _db.session.commit()
            print(f"📦 种子源: {len(sources)} 个")
        
        if NewsArticle.query.count() == 0:
            import flask
            from app.services.data_updater import DataUpdater
            updater = DataUpdater()
            updater.context_app = flask.current_app._get_current_object()
            added = updater.generate_batch(10)
            print(f"📦 种子文章: {added} 篇")
    except Exception as e:
        print(f"⚠️ 建表异常: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f"🚀 启动服务: 0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
