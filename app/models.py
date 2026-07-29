from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar_url = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    wechat_openid = db.Column(db.String(64), unique=True, nullable=True)
    wechat_nickname = db.Column(db.String(64), default="")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class NewsSource(db.Model):
    __tablename__ = 'news_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False, unique=True)
    source_type = db.Column(db.Enum('RSS', 'WEB', 'API'), default='WEB')
    crawl_interval = db.Column(db.Integer, default=5)
    status = db.Column(db.Enum('启用', '停用', '失效'), default='启用')
    category = db.Column(db.String(50), default='综合')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    last_crawl_at = db.Column(db.DateTime, comment='最近采集时间')
    last_error = db.Column(db.String(300), default='', comment='最近错误')
    article_count = db.Column(db.Integer, default=0, comment='累计文章数')
    
    articles = db.relationship('NewsArticle', backref='source', lazy=True)

class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime)
    author = db.Column(db.String(50))
    source_site = db.Column(db.String(100))
    url = db.Column(db.String(500))
    source_id = db.Column(db.Integer, db.ForeignKey('news_sources.id'))
    collected_at = db.Column(db.DateTime, default=datetime.now)
    is_duplicate = db.Column(db.Boolean, default=False)
    is_saved = db.Column(db.Boolean, default=False, comment='用户收藏')
    category = db.Column(db.String(50), default='综合')

class WechatUserInfo(db.Model):
    __tablename__ = 'wechat_user_infos'
    
    id = db.Column(db.Integer, primary_key=True)
    openid = db.Column(db.String(64), unique=True, nullable=False)
    nickname = db.Column(db.String(64))
    avatar_url = db.Column(db.String(500))
    gender = db.Column(db.Integer, default=0)
    region = db.Column(db.String(100))
    collected_at = db.Column(db.DateTime, default=datetime.now)
    authorized_at = db.Column(db.DateTime)


class WeChatMPAccount(db.Model):
    """关注的公众号账号列表"""
    __tablename__ = 'wechat_mp_accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='公众号名称')
    wxid = db.Column(db.String(100), default='', comment='微信号(gh_xxx)')
    category = db.Column(db.String(50), default='综合', comment='归属分类')
    status = db.Column(db.String(10), default='启用', comment='启用/停用')
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_crawl = db.Column(db.DateTime, comment='最近采集时间')
    crawl_count = db.Column(db.Integer, default=0, comment='累计采集文章数')
