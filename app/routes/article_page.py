from flask import make_response, Blueprint
from app.models import NewsArticle, NewsSource

article_bp = Blueprint('article', __name__)

@article_bp.route('/page/<int:article_id>')
def article_page(article_id):
    article = NewsArticle.query.get_or_404(article_id)
    source = NewsSource.query.get(article.source_id) if article.source_id else None
    category = source.category if source else '综合'
    
    content_text = (article.content or '').replace('\n', '<br>')
    
    back = '<a href="/" style="color:#1a73e8;text-decoration:none">\u2190 \u8fd4\u56de\u9996\u9875</a>'
    
    src_link = ''
    if article.url and '36kr.com' in article.url:
        src_link = ' <a href="' + article.url + '" target="_blank" style="color:#1a73e8">\u67e5\u770b\u539f\u6587 \u2197</a>'
    
    src_info = '\u6765\u6e90: ' + (article.source_site or '-')
    src_info += ' | \u5206\u7c7b: ' + category
    if article.publish_time:
        src_info += ' | ' + article.publish_time.strftime('%Y-%m-%d %H:%M')
    
    title = article.title
    meta = src_info + src_link
    body = content_text
    footer = back + src_link
    
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + title + """ - \u91c7\u96c6\u7cfb\u7edf</title>
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
""" + back + """
<h1>""" + title + """</h1>
<div class="meta">""" + meta + """</div>
<div class="body">""" + body + """</div>
<div class="footer">""" + footer + """</div>
</div></body></html>"""
    
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp
