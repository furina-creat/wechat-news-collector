from flask import Blueprint, request
from app.services.crawler import CrawlerFactory
from app.models import NewsSource, NewsArticle
from app.utils.response import success, error
from app import db

collect_bp = Blueprint('collect', __name__)


@collect_bp.route('/run/<int:source_id>', methods=['POST'])
def run_collect(source_id):
    """手动触发采集指定新闻源"""
    source = NewsSource.query.get_or_404(source_id)
    if source.status != '启用':
        return error('该新闻源已停用或失效, 无法采集')
    
    try:
        crawler = CrawlerFactory.get_crawler(source)
        articles = crawler.run()
        return success({
            'source': source.name,
            'source_id': source.id,
            'collected': len(articles)
        }, '采集完成')
    except Exception as e:
        return error(f'采集失败: {str(e)}', 500)


@collect_bp.route('/run/all', methods=['POST'])
def run_all():
    """触发所有启用的新闻源采集"""
    sources = NewsSource.query.filter_by(status='启用').all()
    if not sources:
        return success([], '没有启用的新闻源')
    
    results = []
    for src in sources:
        try:
            crawler = CrawlerFactory.get_crawler(src)
            articles = crawler.run()
            results.append({
                'source': src.name,
                'source_id': src.id,
                'collected': len(articles),
                'status': 'success'
            })
        except Exception as e:
            results.append({
                'source': src.name,
                'source_id': src.id,
                'error': str(e),
                'status': 'failed'
            })
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    return success({
        'total': len(results),
        'success': success_count,
        'failed': len(results) - success_count,
        'details': results
    }, f'批量采集完成, 成功: {success_count}/{len(results)}')
