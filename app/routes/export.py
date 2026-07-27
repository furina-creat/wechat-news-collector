from flask import Blueprint, request, Response
import json
import csv
from io import StringIO
from app.models import NewsArticle
from app.utils.response import error

export_bp = Blueprint('export', __name__)


@export_bp.route('/news/json', methods=['GET'])
def export_news_json():
    """导出新闻为 JSON 文件"""
    articles = NewsArticle.query.order_by(NewsArticle.collected_at.desc()).limit(1000).all()
    data = [{
        'title': a.title,
        'content': a.content,
        'publish_time': a.publish_time.isoformat() if a.publish_time else None,
        'source': a.source_site,
        'author': a.author,
        'url': a.url,
        'collected_at': a.collected_at.isoformat() if a.collected_at else None
    } for a in articles]
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=news_export.json'}
    )


@export_bp.route('/news/csv', methods=['GET'])
def export_news_csv():
    """导出新闻为 CSV 文件"""
    articles = NewsArticle.query.order_by(NewsArticle.collected_at.desc()).limit(1000).all()
    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['标题', '内容摘要', '发布时间', '来源', '作者', '链接', '采集时间'])
    for a in articles:
        content_preview = (a.content[:100] + '...') if a.content and len(a.content) > 100 else a.content
        writer.writerow([
            a.title,
            content_preview,
            a.publish_time.isoformat() if a.publish_time else '',
            a.source_site or '',
            a.author or '',
            a.url or '',
            a.collected_at.isoformat() if a.collected_at else ''
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': 'attachment; filename=news_export.csv'}
    )
