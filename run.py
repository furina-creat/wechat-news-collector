import os, sys, threading
from datetime import datetime

_base = os.path.dirname(__file__)
sys.path.insert(0, _base)

# 确保数据库目录存在
os.makedirs(os.path.join(_base, 'instance'), exist_ok=True)

from app import create_app, db
from app.services.collect_task import CollectScheduler
from app.services.crawler import CrawlerFactory
from app.models import NewsSource, NewsArticle

app = create_app()

# ---- 初始化数据库 ----
with app.app_context():
    try:
        db.create_all()
        print(f"[{datetime.now()}] ✅ 数据库就绪")
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ 建表异常: {e}")


# ---- 后台启动采集调度器 ----
def _start_scheduler(app):
    """在后台线程中启动调度器，并尝试首次采集。"""
    with app.app_context():
        scheduler = CollectScheduler(app)
        scheduler.start()

        # 首次采集：抓取前 3 个活跃新闻源
        try:
            sources = NewsSource.query.filter_by(status='启用').all()
            total_new = 0
            for src in sources:
                if 'example.com' in (src.url or ''):
                    continue
                try:
                    crawler = CrawlerFactory.get_crawler(src)
                    articles = crawler.run()
                    total_new += len(articles)
                    print(f"[{datetime.now()}] ✅ 首次采集 [{src.name}]: {len(articles)} 篇")
                except Exception as e:
                    print(f"[{datetime.now()}] ⚠️ 采集跳过 [{src.name}]: {str(e)[:60]}")
            print(f"[{datetime.now()}] 📊 首次采集完成，共新增 {total_new} 篇文章")
            total = NewsSource.query.count()
            print(f"[{datetime.now()}] 📊 当前共有 {NewsArticle.query.count()} 篇文章，{total} 个新闻源")
        except Exception as e:
            print(f"[{datetime.now()}] ⚠️ 首次采集异常: {e}")


threading.Thread(target=_start_scheduler, args=(app,), daemon=True).start()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(debug=False, host='0.0.0.0', port=port)
