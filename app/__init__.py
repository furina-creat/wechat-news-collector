from flask import Flask, render_template, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['SECRET_KEY'] = 'collector-secret-key-2026'
    
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

    return app
