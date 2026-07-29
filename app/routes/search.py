from flask import Blueprint, request, make_response
from datetime import datetime, timedelta
from app.models import NewsArticle, WechatUserInfo, NewsSource
from app.utils.response import success

search_bp = Blueprint('search', __name__)


@search_bp.route('/news', methods=['GET'])
def search_news():
    """搜索新闻（关键词匹配标题和正文）"""
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return success([], '请提供搜索关键词')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # 限制最大返回条数
    
    pagination = NewsArticle.query.filter(
        NewsArticle.title.contains(keyword) | 
        NewsArticle.content.contains(keyword)
    ).order_by(NewsArticle.collected_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    data = [{
        'id': a.id,
        'title': a.title,
        'content': (a.content[:300] + '...') if a.content and len(a.content) > 300 else a.content,
        'publish_time': a.publish_time.isoformat() if a.publish_time else None,
        'source': a.source_site,
        'url': a.url,
        'author': a.author,
        'collected_at': a.collected_at.isoformat() if a.collected_at else None
    } for a in pagination.items]
    
    return success({
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'items': data
    })


@search_bp.route('/wechat', methods=['GET'])
def search_wechat():
    """搜索微信用户信息（仅示例，实际需权限控制）"""
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return success([])
    
    users = WechatUserInfo.query.filter(
        WechatUserInfo.nickname.contains(keyword)
    ).limit(50).all()
    
    data = [{
        'openid': u.openid,
        'nickname': u.nickname,
        'region': u.region,
        'gender': u.gender,
        'avatar': u.avatar_url,
        'collected_at': u.collected_at.isoformat() if u.collected_at else None
    } for u in users]
    return success(data)

@search_bp.route('/by_category', methods=['GET'])
def search_by_category():
    """按分类获取文章"""
    category = request.args.get('category', '综合')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Find sources in this category
    cutoff = datetime.now() - timedelta(days=180)
    pagination = NewsArticle.query.filter(
        NewsArticle.category == category,
        NewsArticle.collected_at >= cutoff
    ).order_by(NewsArticle.collected_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    items = [{
        'id': a.id,
        'title': a.title,
        'content': (a.content[:300] + '...') if a.content and len(a.content) > 300 else a.content,
        'publish_time': a.publish_time.isoformat() if a.publish_time else None,
        'source': a.source_site,
        'url': a.url,
        'collected_at': a.collected_at.isoformat() if a.collected_at else None
    } for a in pagination.items]
    
    return success({
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'items': items
    })

@search_bp.route('/sources_by_category', methods=['GET'])
def sources_by_category():
    """按分类获取新闻源"""
    category = request.args.get('category', '综合')
    sources = NewsSource.query.filter_by(category=category).all()
    data = [{
        'id': s.id,
        'name': s.name,
        'type': s.source_type,
        'status': s.status,
        'interval': s.crawl_interval
    } for s in sources]
    return success(data)

@search_bp.route('/article/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """获取单篇文章详情"""
    article = NewsArticle.query.get_or_404(article_id)
    return success({
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'publish_time': article.publish_time.isoformat() if article.publish_time else None,
        'source': article.source_site,
        'author': article.author,
        'url': article.url,
        'collected_at': article.collected_at.isoformat() if article.collected_at else None
    })

@search_bp.route('/page/<int:article_id>')
def article_page(article_id):
    from flask import make_response
    article = NewsArticle.query.get_or_404(article_id)
    source = NewsSource.query.get(article.source_id) if article.source_id else None
    category = source.category if source else '综合'
    content_text = (article.content or '').replace('\n', '<br>')
    
    back = '<a href="/" style="color:#1a73e8;text-decoration:none">\u2190 \u8fd4\u56de\u9996\u9875</a>'
    src_link = ''
    if article.url and '36kr.com' in article.url:
        src_link = '<a href="' + article.url + '" target="_blank" style="color:#1a73e8;margin-left:16px">\u67e5\u770b\u539f\u6587 \u2197</a>'
    
    src_info = '来\u6e90: ' + (article.source_site or '-') + ' | 分\u7c7b: ' + category
    if article.publish_time:
        src_info += ' | ' + article.publish_time.strftime('%Y-%m-%d %H:%M')
    
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>''' + article.title + ''' - 采集系统</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
body{background:#f5f5f5;color:#333;padding:40px 20px}
.card{max-width:800px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 2px 12px rgba(0,0,0,0.08)}
h1{font-size:24px;margin-bottom:16px;color:#1a1a2e;line-height:1.4}
.meta{font-size:14px;color:#999;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #eee}
.body{font-size:16px;line-height:1.9;color:#444}
.footer{margin-top:32px;padding-top:16px;border-top:1px solid #eee;font-size:14px;color:#999}
</style></head>
<body><div class="card">
''' + back + '''
<h1>''' + article.title + '''</h1>
<div class="meta">''' + src_info + src_link + '''</div>
<div class="body">''' + content_text + '''</div>
<div class="footer">''' + back + src_link + '''</div>
</div></body></html>'''
    
    resp = make_response(html_content)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp
