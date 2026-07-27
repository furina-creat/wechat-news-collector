import re


def is_valid_url(url):
    """简单的URL格式校验"""
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'[a-zA-Z0-9.-]+'  # domain
        r'(:\d+)?'  # optional port
        r'(/[a-zA-Z0-9._~:/?#\[\]@!$&\'()*+,;=-]*)?$'
    )
    return bool(pattern.match(url))


def validate_news_source_data(data):
    """校验新闻源添加/更新数据"""
    errors = []
    
    if 'name' in data and not data['name'].strip():
        errors.append('新闻源名称不能为空')
    if 'name' in data and len(data['name']) > 100:
        errors.append('新闻源名称不能超过100个字符')
    
    if 'url' in data:
        if not data['url'].strip():
            errors.append('URL不能为空')
        elif not is_valid_url(data['url']):
            errors.append('URL格式不正确')
    
    if 'type' in data and data['type'] not in ('RSS', 'WEB', 'API'):
        errors.append('源类型必须为 RSS/WEB/API')
    
    if 'interval' in data and (not isinstance(data['interval'], int) or data['interval'] < 1):
        errors.append('采集频率必须为正整数（分钟）')
    
    return errors
