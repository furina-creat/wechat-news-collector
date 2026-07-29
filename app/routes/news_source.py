from flask import Blueprint, request
from app import db
from app.models import NewsSource
from app.utils.response import success, error
from app.utils.validators import validate_news_source_data, is_valid_url

source_bp = Blueprint('source', __name__)


@source_bp.route('/', methods=['GET'])
def list_sources():
    """列出所有新闻源"""
    sources = NewsSource.query.all()
    data = [{
        'id': s.id,
        'name': s.name,
        'url': s.url,
        'type': s.source_type,
        'interval': s.crawl_interval,
        'status': s.status,
        'created_at': s.created_at.isoformat() if s.created_at else None
    } for s in sources]
    return success(data)


@source_bp.route('/', methods=['POST'])
def add_source():
    """添加新闻源"""
    json_data = request.json
    if not json_data:
        return error('请求体不能为空')
    
    if 'name' not in json_data or 'url' not in json_data:
        return error('缺少必填字段: name, url')
    
    # 参数校验
    errors = validate_news_source_data(json_data)
    if errors:
        return error('; '.join(errors))
    
    # 检查是否已存在
    if NewsSource.query.filter_by(url=json_data['url']).first():
        return error('该新闻源已存在')
    
    source = NewsSource(
        name=json_data['name'],
        url=json_data['url'],
        source_type=json_data.get('type', 'WEB'),
        crawl_interval=json_data.get('interval', 5),
        status=json_data.get('status', '启用')
    )
    db.session.add(source)
    db.session.commit()
    return success({'id': source.id}, '添加成功')


@source_bp.route('/<int:sid>', methods=['GET'])
def get_source(sid):
    """获取单个新闻源详情"""
    source = NewsSource.query.get_or_404(sid)
    data = {
        'id': source.id,
        'name': source.name,
        'url': source.url,
        'type': source.source_type,
        'interval': source.crawl_interval,
        'status': source.status,
        'created_at': source.created_at.isoformat() if source.created_at else None,
        'updated_at': source.updated_at.isoformat() if source.updated_at else None,
        'article_count': len(source.articles)
    }
    return success(data)


@source_bp.route('/<int:sid>', methods=['PUT'])
def update_source(sid):
    """更新新闻源"""
    source = NewsSource.query.get_or_404(sid)
    json_data = request.json
    if not json_data:
        return error('请求体不能为空')
    
    errors = validate_news_source_data(json_data)
    if errors:
        return error('; '.join(errors))
    
    if 'name' in json_data:
        source.name = json_data['name']
    if 'url' in json_data:
        # 检查新URL是否与其他源冲突
        existing = NewsSource.query.filter_by(url=json_data['url']).first()
        if existing and existing.id != sid:
            return error('该URL已被其他新闻源使用')
        source.url = json_data['url']
    if 'type' in json_data:
        source.source_type = json_data['type']
    if 'interval' in json_data:
        source.crawl_interval = json_data['interval']
    if 'status' in json_data:
        source.status = json_data['status']
    
    db.session.commit()
    return success(message='更新成功')


@source_bp.route('/<int:sid>', methods=['DELETE'])
def delete_source(sid):
    """删除新闻源（同时删除关联的新闻文章）"""
    source = NewsSource.query.get_or_404(sid)
    db.session.delete(source)  # 级联删除关联articles（需在model定义cascade）
    db.session.commit()
    return success(message='删除成功')

@source_bp.route('/defaults', methods=['POST'])
def add_default_sources():
    """一键添加默认新闻源"""
    DEFAULT_SOURCES = [
        {"name": "知乎日报", "url": "https://www.zhihu.com/rss/daily", "type": "RSS", "interval": 60},
        {"name": "新浪新闻", "url": "https://rss.sina.com.cn/sina_all.xml", "type": "RSS", "interval": 30},
        {"name": "澎湃新闻", "url": "https://www.thepaper.cn/rss/", "type": "RSS", "interval": 30},
        {"name": "果壳网", "url": "https://www.guokr.com/rss/", "type": "RSS", "interval": 60},
        {"name": "36氪", "url": "https://36kr.com/feed", "type": "RSS", "interval": 60},
    ]
    count = 0
    for s in DEFAULT_SOURCES:
        exists = NewsSource.query.filter_by(url=s["url"]).first()
        if not exists:
            source = NewsSource(name=s["name"], url=s["url"], source_type=s["type"], crawl_interval=s["interval"])
            db.session.add(source)
            count += 1
    db.session.commit()
    return success({"added": count, "total": NewsSource.query.count()}, f"添加了 {count} 个默认新闻源")


@source_bp.route('/health', methods=['GET'])
def source_health():
    sources = NewsSource.query.order_by(NewsSource.last_crawl_at.desc().nullslast()).all()
    return success([{
        'id': s.id, 'name': s.name, 'url': s.url[:50],
        'type': s.source_type, 'status': s.status,
        'crawl_interval': s.crawl_interval,
        'last_crawl': s.last_crawl_at.isoformat() if s.last_crawl_at else None,
        'last_error': s.last_error or '',
        'article_count': s.article_count or 0,
    } for s in sources])


@source_bp.route('/saved', methods=['GET'])
def list_saved():
    from app.models import NewsArticle
    articles = NewsArticle.query.filter_by(is_saved=True).order_by(NewsArticle.collected_at.desc()).limit(100).all()
    return success([{
        'id': a.id, 'title': a.title, 'content': (a.content or '')[:120],
        'source': a.source_site, 'category': a.category,
        'url': a.url,
        'collected_at': a.collected_at.isoformat() if a.collected_at else None,
    } for a in articles])


@source_bp.route('/<int:article_id>/save', methods=['POST'])
def toggle_save(article_id):
    from app.models import NewsArticle
    article = NewsArticle.query.get_or_404(article_id)
    article.is_saved = not article.is_saved
    db.session.commit()
    return success({'id': article.id, 'is_saved': article.is_saved})


@source_bp.route('/recategorize', methods=['POST'])
def recategorize_all():
    """重新分类所有已有文章（修复爬虫关键词收紧前的错误分类）。"""
    from app.models import NewsArticle
    import re as _re
    count = 0
    for a in NewsArticle.query.all():
        t = (a.title or '') + ' ' + (a.content or '')
        new_cat = '综合'
        if any(k in t for k in ['考研','考公','公务员','行测','招生','研究生','复试','考点','备考','录取','分数线','国考','省考','申论','事业单位','教师招聘']):
            new_cat = '考公考研'
        elif any(k in t for k in ['招聘','求职','简历','就业','实习','校招','管培生','应届生','秋招','春招']):
            new_cat = '应届求职'
        elif any(k in t for k in ['股票','股市','大盘','涨停','跌停','上证','深证','创业板','科创板','恒生','A股','港股','美股','基金','ETF','牛市','熊市','涨幅','跌幅','成交额','板块','指数','开盘','收盘','投资','估值','行情','回调','反弹','仓位','持仓']):
            new_cat = '股票市场'
        if a.category != new_cat:
            a.category = new_cat
            count += 1
    db.session.commit()
    return success({'recategorized': count, 'total': NewsArticle.query.count()})
