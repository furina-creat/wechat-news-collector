#!/usr/bin/env python3
"""
微信与新闻信息采集系统 - 启动器
双击 .app 即可启动服务器并打开浏览器
"""
import webbrowser
import threading
import time
import sys
import os

# 将项目目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://localhost:5050')

if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()
    print('📡 微信与新闻信息采集系统 已启动')
    print('🌐 浏览器已自动打开: http://localhost:5050')
    print('按 Ctrl+C 停止服务')
    app.run(debug=False, host='127.0.0.1', port=5000)
