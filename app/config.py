import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    # 默认使用 SQLite（方便本地测试），设为 DATABASE_URL 环境变量可切换 MySQL
    # Railway 部署时会自动设置 DATABASE_URL 为 PostgreSQL
    _db_url = os.getenv('DATABASE_URL', 'sqlite:///wechat_news.db')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 微信开放平台配置
    WECHAT_APP_ID = os.getenv('WECHAT_APP_ID', '')
    WECHAT_APP_SECRET = os.getenv('WECHAT_APP_SECRET', '')
    
    # 微信公众号消息服务配置
    WECHAT_MP_TOKEN = os.getenv('WECHAT_MP_TOKEN', '')
    
    # 采集配置
    MAX_CONCURRENT_SOURCES = 10
    DEFAULT_CRAWL_INTERVAL = 5  # 分钟
    REQUEST_TIMEOUT = 30
    RETRY_TIMES = 3
