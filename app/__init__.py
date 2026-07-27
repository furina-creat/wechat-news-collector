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
                    ("网易新闻","https://c.m.163.com/api/subscribe/feed/"),
                    ("新浪教育","https://rss.sina.com.cn/edu/edu.xml"),
                    ("新华网","https://www.xinhuanet.com/rss/edu.xml"),
                    ("人民教育","https://edu.people.com.cn/rss/edu.xml"),
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

    @app.route('/api/seed')
    def seed_html():
        from app.models import NewsSource, NewsArticle
        from datetime import datetime, timedelta
        import random
        
        added = {'sources': 0, 'articles': 0}
        
        all_sources = [
            ("36氪","https://36kr.com/feed"),("澎湃新闻","https://www.thepaper.cn/rss/"),
            ("知乎日报","https://www.zhihu.com/rss/daily"),("新浪新闻","https://rss.sina.com.cn/sina_all.xml"),
            ("虎嗅","https://www.huxiu.com/rss/1.xml"),("果壳网","https://www.guokr.com/rss/"),
            ("新浪财经","https://rss.sina.com.cn/finance/finance.xml"),
            ("新浪科技","https://rss.sina.com.cn/tech/tech.xml"),
            ("新浪教育","https://rss.sina.com.cn/edu/edu.xml"),
            ("腾讯科技","https://rss.news.qq.com/news/tech/"),
            ("网易科技","https://rss.sina.com.cn/tech/tech.xml"),
            ("新浪体育","https://rss.sina.com.cn/sports/sports.xml"),
            ("36氪快讯","https://36kr.com/newsflashes"),
        ]
        for n,u in all_sources:
            if not NewsSource.query.filter_by(url=u).first():
                db.session.add(NewsSource(name=n,url=u,source_type='RSS',crawl_interval=60,category='综合'))
                added['sources'] += 1
        db.session.commit()
        
        seeds = [
            ("考研国家线公布","2026年考研国家线公布经济涨6分","考公考研"),
            ("行测备考攻略","行测四大模块备考方法详解","考公考研"),
            ("考研英语阅读策略","阅读占考研英语40%三大策略","考公考研"),
            ("考研数学复习规划","高数线代概率三轮复习法","考公考研"),
            ("政治时政重点","关注重要政策与热点话题","考公考研"),
            ("国考报名启动","2026年国考10月报名启动","考公考研"),
            ("复试自我介绍","考研复试英语面试准备","考公考研"),
            ("事业单位公基备考","公基七大模块备考方法","考公考研"),
            ("考研调剂攻略","调剂系统3月底开放","考公考研"),
            ("公务员面试答题","结构化面试答题框架","考公考研"),
            ("秋招时间线与策略","校招各阶段准备重点","应届求职"),
            ("互联网大厂面试","BAT面试全流程经验分享","应届求职"),
            ("简历优化指南","HR视角简历撰写要点","应届求职"),
            ("国企校招攻略","国企招聘流程详解","应届求职"),
            ("产品经理求职","产品经理入门与面试","应届求职"),
            ("薪资谈判技巧","应届生薪资谈判方法","应届求职"),
            ("校招笔试分享","互联网笔试考察内容","应届求职"),
            ("职场新人融入","入职第一周注意事项","应届求职"),
            ("A股三大指数收跌","A股收跌半导体领跌","股票市场"),
            ("央行货币政策报告","央行稳健货币政策","股票市场"),
            ("港股科技股大涨","恒生科技指数涨超3%","股票市场"),
            ("基金市场周报","主动权益基金上涨","股票市场"),
            ("北向资金流入","外资加仓A股","股票市场"),
            ("创业板指大涨","创业板指涨超2%","股票市场"),
        ]
        for i,(t,c,cat) in enumerate(seeds):
            if not NewsArticle.query.filter_by(title=t).first():
                db.session.add(NewsArticle(
                    title=t,content=c,category=cat,
                    source_site=random.choice(['澎湃新闻','36氪','新浪新闻']),
                    url=t+'',
                    collected_at=datetime.now()-timedelta(minutes=len(seeds)-i)))
                added['articles'] += 1
        db.session.commit()
        
        from flask import make_response
        html = '<!DOCTYPE html><html><head><meta charset=utf-8><title>初始化完成</title>'
        html += '<style>body{font-family:-apple-system,sans-serif;padding:40px;background:#f5f5f5;color:#333}'
        html += '.card{background:#fff;border-radius:12px;padding:40px;max-width:600px;margin:0 auto;box-shadow:0 2px 12px rgba(0,0,0,0.08)}'
        html += 'h1{color:#1a73e8}.ok{color:#22c55e;font-size:48px}.btn{display:inline-block;background:#1a73e8;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:20px}'
        html += '</style></head><body><div class="card">'
        html += '<div class="ok">&#10003;</div><h1>系统初始化完成</h1>'
        html += f'<p>新增 {added["sources"]} 个新闻源</p>'
        html += f'<p>新增 {added["articles"]} 篇文章</p>'
        html += f'<p>当前共有 {NewsSource.query.count()} 个源, {NewsArticle.query.count()} 篇文章</p>'
        html += '<a href="/" class="btn">返回首页</a>'
        html += '</div></body></html>'
        resp = make_response(html)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        return resp

    @app.route('/api/seed')
    def force_seed():
        from app.models import NewsSource, NewsArticle
        from datetime import datetime, timedelta
        import random
        try:
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
                ("网易新闻","https://c.m.163.com/api/subscribe/feed/"),
                ("新华网","https://www.xinhuanet.com/rss/edu.xml"),("人民教育","https://edu.people.com.cn/rss/edu.xml"),
            ]
            count_s = 0
            for n,u in all_sources:
                if not NewsSource.query.filter_by(url=u).first():
                    db.session.add(NewsSource(name=n,url=u,source_type='RSS',crawl_interval=60,category='综合'))
                    count_s += 1
            db.session.commit()
            
            if NewsArticle.query.count() < 50:
                now = datetime.now()
                seeds = [
                    ("考研国家线公布","2026年考研国家线公布，经济学涨6分，工学持平。法学、管理学等热门专业分数线稳中有升。考生可根据自身情况选择调剂院校，重点关注B区院校。","考公考研"),
                    ("行测备考攻略","行测涵盖言语理解、数量关系、判断推理、资料分析四大模块。言语理解重点掌握主旨概括和逻辑填空，数量关系重点掌握工程问题和行程问题。","考公考研"),
                    ("考研英语阅读策略","阅读占考研英语40%，是拉开差距的关键。三大策略：定位法快速定位原文、排除法快速排除干扰项、主旨法把握文章核心。","考公考研"),
                    ("考研数学复习规划","高数占比56%、线代22%、概率22%。基础阶段掌握教材习题，强化阶段专项训练，冲刺阶段真题模拟。","考公考研"),
                    ("政治时政重点","重点关注中央经济工作会议、科技创新政策、生态文明建设等时政热点。建议关注新华社、人民日报报道。","考公考研"),
                    ("国考报名启动","2026年国考报名10月中旬启动，招录规模扩大，重点向基层倾斜。网上报名、资格初审、缴费、打印准考证。","考公考研"),
                    ("复试英语自我介绍","考研复试英语面试需要准备自我介绍范文，突出学术背景和研究兴趣，时长控制在2分钟左右。","考公考研"),
                    ("事业单位公基备考","公共基础知识涵盖政治法律经济管理公文人文科技七大模块，需要系统学习和长期积累。","考公考研"),
                    ("考研调剂攻略","调剂系统3月底至4月底开放，B区院校和冷门专业调剂成功率更高，建议提前联系导师。","考公考研"),
                    ("公务员面试答题","结构化面试常见题型包括综合分析、组织管理、人际关系、应急应变。答题要条理清晰层次分明。","考公考研"),
                    ("秋招时间线与策略","7-8月提前批、9-10月正式批、11月补录。提前准备简历、了解企业、刷题、模拟面试。","应届求职"),
                    ("互联网大厂面试","BAT面试经验分享：技术面考算法和项目，交叉面考技术视野，HR面考综合素质。","应届求职"),
                    ("简历优化指南","HR浏览简历仅6秒，要用STAR法则量化成果，突出与岗位匹配的能力和经验。","应届求职"),
                    ("国企校招攻略","国企招聘流程：网申→笔试→面试→体检→政审→公示。重点关注中国烟草、国家电网等。","应届求职"),
                    ("产品经理求职","入门建议：系统学习产品方法论，做产品分析报告作为作品集，参加产品竞赛或实习。","应届求职"),
                    ("薪资谈判技巧","提前了解行业薪资水平，谈判着眼于总包而非月薪，礼貌自信表达自身价值。","应届求职"),
                    ("校招笔试分享","互联网大厂笔试包括选择题和编程题，考察计算机网络、操作系统、数据库等基础知识。","应届求职"),
                    ("职场新人融入","入职第一周主动了解公司文化和业务流程，积极沟通交流，定期汇报工作进展。","应届求职"),
                    ("A股三大指数收跌","上证跌1.2%深证跌0.8%，两市成交额突破万亿，半导体新能源板块跌幅居前。","股票市场"),
                    ("央行货币政策报告","央行强调稳健货币政策，保持流动性合理充裕，加大对实体经济支持力度。","股票市场"),
                    ("北向资金大幅流入","北向资金净流入超百亿，外资持续看好A股市场，重点加仓新能源消费板块。","股票市场"),
                    ("港股科技股大涨","恒生科技指数涨超3%，互联网巨头发布超预期财报，提振市场信心。","股票市场"),
                    ("基金市场周报","主动权益类基金平均收益率小幅上涨，建议关注优质赛道龙头基金。","股票市场"),
                    ("创业板指涨超2%","创业板指今日涨超2%，科技股表现强势，市场情绪回暖。","股票市场"),
                ]
                for i,(t,c,cat) in enumerate(seeds):
                    db.session.add(NewsArticle(title=t,content=c,category=cat,source_site=random.choice(['澎湃新闻','36氪','新浪新闻']),url='https://www.baidu.com/s?wd='+t[:10].replace(' ','+'),collected_at=now-timedelta(minutes=i*10)))
                db.session.commit()
                return jsonify({'code':200,'message':f'添加了{count_s}个源和{len(seeds)}篇文章'})
            return jsonify({'code':200,'message':f'添加了{count_s}个源（文章已存在）'})
        except Exception as e:
            return jsonify({'code':500,'message':str(e)})

    return app
