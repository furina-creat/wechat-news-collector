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
