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
        # 迁移：为新加的列做 ALTER TABLE（兼容已有数据库）
        _migrate_db()
        print(f"[{datetime.now()}] ✅ 数据库就绪")
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ 建表异常: {e}")


def _migrate_db():
    """给已有数据库添加缺失的列（不破坏现有数据）。"""
    from sqlalchemy import inspect, text as sa_text
    inspector = inspect(db.engine)

    migrates = {
        "news_sources": [
            ("last_crawl_at", "DATETIME"),
            ("last_error", "VARCHAR(300) DEFAULT ''"),
            ("article_count", "INTEGER DEFAULT 0"),
        ],
        "news_articles": [
            ("is_saved", "INTEGER DEFAULT 0"),
        ],
    }
    for table, columns in migrates.items():
        existing = {c["name"] for c in inspector.get_columns(table)}
        for col_name, col_type in columns:
            if col_name not in existing:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(sa_text(
                            f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                        ))
                        conn.commit()
                    print(f"  ✅ 迁移: {table}.{col_name}")
                except Exception as e:
                    print(f"  ⚠️ 迁移跳过 {table}.{col_name}: {e}")


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

        # 首次采集公众号文章
        try:
            from app.models import WeChatMPAccount
            from app.services.mp_collector import crawl_all_accounts as crawl_wechat_mp
            if WeChatMPAccount.query.count() == 0:
                db.session.add(WeChatMPAccount(name='重庆招考', category='考公考研'))
                db.session.commit()
                print(f"[{datetime.now()}] 📡 已添加默认公众号「重庆招考」")
            mp_results = crawl_wechat_mp()
            print(f"[{datetime.now()}] 📡 公众号采集完成: {len(mp_results)} 个账号")
        except Exception as e:
            print(f"[{datetime.now()}] ⚠️ 公众号采集跳过: {e}")


threading.Thread(target=_start_scheduler, args=(app,), daemon=True).start()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(debug=False, host='0.0.0.0', port=port)
