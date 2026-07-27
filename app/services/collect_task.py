import threading
import time
from datetime import datetime
from app.models import NewsSource
from app.services.crawler import CrawlerFactory
from app import db


class CollectScheduler:
    """
    简易采集调度器
    实际生产环境建议使用 APScheduler 或 Celery
    """
    
    def __init__(self, app):
        self.app = app
        self._running = False
        self._thread = None
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[{datetime.now()}] 采集调度器已启动")
    
    def stop(self):
        self._running = False
        print(f"[{datetime.now()}] 采集调度器已停止")
    
    def _loop(self):
        while self._running:
            with self.app.app_context():
                try:
                    self._check_and_collect()
                except Exception as e:
                    print(f"调度循环异常: {e}")
            time.sleep(300)  # 每分钟检查一次
    
    def _check_and_collect(self):
        """检查各新闻源是否需要采集"""
        sources = NewsSource.query.filter_by(status='启用').all()
        now = datetime.now()
        for source in sources:
            # 简单判断：检查是否有上一篇文章及其采集时间
            last_article = source.articles[-1] if source.articles else None
            if last_article:
                elapsed = (now - last_article.collected_at).total_seconds() / 60
                if elapsed < source.crawl_interval:
                    continue  # 未到采集间隔
            
            try:
                crawler = CrawlerFactory.get_crawler(source)
                articles = crawler.run()
                print(f"[{now}] 采集 [{source.name}]: 新增 {len(articles)} 篇")
            except Exception as e:
                print(f"[{now}] 采集失败 [{source.name}]: {e}")
