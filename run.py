import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db

app = create_app()

# 确保启动时创建表
with app.app_context():
    try:
        db.create_all()
        print("✅ 数据库表已就绪")
    except Exception as e:
        print(f"⚠️ 建表异常: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f"🚀 启动服务: 0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
