"""
py2app 打包配置
"""
from setuptools import setup

APP = ['app/launcher.py']
DATA_FILES = [
    ('app/templates', ['app/templates/index.html']),
    ('app/static', ['app/static/style.css', 'app/static/app.js']),
    ('app/routes', ['app/routes/__init__.py', 'app/routes/wechat.py',
                    'app/routes/news_source.py', 'app/routes/collect.py',
                    'app/routes/search.py', 'app/routes/export.py']),
    ('app/services', ['app/services/__init__.py', 'app/services/wechat_service.py',
                       'app/services/crawler.py', 'app/services/collect_task.py']),
    ('app/utils', ['app/utils/__init__.py', 'app/utils/response.py',
                    'app/utils/validators.py']),
    ('.', ['.env.example']),
]
OPTIONS = {
    'argv_emulation': False,
    'packages': ['flask', 'sqlalchemy', 'pymysql', 'requests', 'bs4', 'lxml',
                 'dotenv', 'flask_sqlalchemy', 'flask_migrate'],
    'includes': ['app', 'app.config', 'app.models', 'app.routes',
                 'app.services', 'app.utils'],
    'excludes': ['tkinter', 'matplotlib', 'scipy', 'PIL', 'cv2'],
    'plist': {
        'CFBundleName': '采集管理系统',
        'CFBundleDisplayName': '微信与新闻信息采集系统',
        'CFBundleIdentifier': 'com.collector.wechat-news',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
    'site_packages': True,
}

setup(
    name='采集管理系统',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
