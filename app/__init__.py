from flask import Flask, render_template, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['SECRET_KEY'] = 'collector-secret-key-2026'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.routes.wechat import wechat_bp
    from app.routes.news_source import source_bp
    from app.routes.collect import collect_bp
    from app.routes.search import search_bp
    from app.routes.export import export_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(wechat_bp, url_prefix='/api/wechat')
    app.register_blueprint(source_bp, url_prefix='/api/source')
    app.register_blueprint(collect_bp, url_prefix='/api/collect')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    
    # Home page
    @app.route('/')
    def index():
        return render_template('index.html')

    # API status
    @app.route('/api/status')
    def api_status():
        return jsonify({'status': 'running', 'message': 'WeChat & News Collector API'})

    # Test route
    @app.route('/ping')
    def ping():
        return 'pong'

    # Article detail page
    @app.route('/page/<int:article_id>')
    def article_page(article_id):
        from app.models import NewsArticle, NewsSource
        
        article = NewsArticle.query.get_or_404(article_id)
        source = NewsSource.query.get(article.source_id)
        category = source.category if source else '综合'
        
        c = (article.content or '').replace('\n', '<br>')
        back = '<a href="/" style="color:#1a73e8;text-decoration:none">\u2190 \u8fd4\u56de\u9996\u9875</a>'
        
        src_link = ''
        if article.url and '36kr.com' in article.url:
            src_link = ' <a href="' + article.url + '" target="_blank" style="color:#1a73e8">\u67e5\u770b\u539f\u6587 \u2197</a>'
        
        info = '\u6765\u6e90: ' + (article.source_site or '-')
        info += ' | \u5206\u7c7b: ' + category
        if article.publish_time:
            info += ' | ' + article.publish_time.strftime('%Y-%m-%d %H:%M')
        
        title = article.title
        html_content = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head><meta charset="UTF-8">'
            + '<title>' + title + '</title>\n<style>\n'
            + '*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}\n'
            + 'body{background:#f5f5f5;color:#333;padding:40px 20px}\n'
            + '.card{max-width:800px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 2px 12px rgba(0,0,0,0.08)}\n'
            + 'h1{font-size:24px;margin-bottom:16px;color:#1a1a2e;line-height:1.4}\n'
            + '.meta{font-size:14px;color:#999;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #eee}\n'
            + '.body{font-size:16px;line-height:1.9;color:#444}\n'
            + '.footer{margin-top:32px;padding-top:16px;border-top:1px solid #eee;font-size:14px;color:#999}\n'
            + '</style>\n</head>\n<body><div class="card">\n'
            + back + '\n<h1>' + title + '</h1>\n<div class="meta">' + info + src_link + '</div>\n'
            + '<div class="body">' + c + '</div>\n<div class="footer">' + back + src_link + '</div>\n'
            + '</div>\n</body>\n</html>')
        
        resp = make_response(html_content)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        return resp

    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # 种子数据（首次运行自动创建）
    with app.app_context():
        from app.models import NewsSource, NewsArticle
        from datetime import datetime
        try:
        # 添加种子源（检查每个源的URL是否已存在，避免重复）
            all_sources = [
                ("36氪","https://36kr.com/feed"),("澎湃新闻","https://www.thepaper.cn/rss/"),
                ("知乎日报","https://www.zhihu.com/rss/daily"),("新浪新闻","https://rss.sina.com.cn/sina_all.xml"),
                ("虎嗅","https://www.huxiu.com/rss/1.xml"),("果壳网","https://www.guokr.com/rss/"),
                ("新浪财经","https://rss.sina.com.cn/finance/finance.xml"),
                ("新浪科技","https://rss.sina.com.cn/tech/tech.xml"),
                ("新浪教育","https://rss.sina.com.cn/edu/edu.xml"),
                ("腾讯科技","https://rss.news.qq.com/news/tech/"),
                ("网易科技","https://rss.sina.com.cn/tech/tech.xml"),
                ("考研帮","https://api.example.com/kaoyan"),("中公教育","https://api.example.com/offcn"),
                ("新东方考研","https://api.example.com/xdf"),("华图教育","https://api.example.com/ht"),
                ("牛客网","https://api.example.com/nowcoder"),("拉勾网","https://api.example.com/lagou"),
                ("智联招聘","https://api.example.com/zhaopin"),("国企招聘网","https://api.example.com/guoqi"),
                ("新浪体育","https://rss.sina.com.cn/sports/sports.xml"),
                ("36氪快讯","https://36kr.com/newsflashes"),
            ]
            for n,u in all_sources:
                if not NewsSource.query.filter_by(url=u).first():
                    db.session.add(NewsSource(name=n,url=u,source_type='RSS',crawl_interval=60,category='综合'))
                db.session.commit()
            if NewsArticle.query.count() == 0:
                now=datetime.now()
                for i,(t,c,cat) in enumerate([
                    ("考研国家线公布","2026年考研国家线公布经济涨","考公考研"),
                    ("行测备考攻略","行测四大模块备考方法详解","考公考研"),
                    ("考研英语阅读策略","阅读占考研英语40%三大策略","考公考研"),
                    ("考研数学复习规划","高数线代概率三轮复习法","考公考研"),
                    ("政治时政热点","关注重要政策与热点话题","考公考研"),
                    ("国考报名时间","2026年国考10月启动","考公考研"),
                    ("秋招时间线与策略","校招各阶段准备重点","应届求职"),
                    ("大厂面试经验","BAT面试全流程经验分享","应届求职"),
                    ("简历优化指南","HR视角简历撰写要点","应届求职"),
                    ("薪资谈判技巧","应届生薪资谈判方法","应届求职"),
                    ("A股收跌","上证跌1.2%半导体领跌","股票市场"),
                    ("央行货币政策","央行披露最新货币政策","股票市场"),
                ]):
                    db.session.add(NewsArticle(title=t,content=c,category=cat,source_site='澎湃新闻',collected_at=now))
                db.session.commit()
        except: pass

    return app
