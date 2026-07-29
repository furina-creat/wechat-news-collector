import os, sys
sys.path.insert(0, os.path.dirname(__file__))

# 确保数据库目录存在
os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

from app import create_app, db
app = create_app()

with app.app_context():
    try:
        db.create_all()
        print("✅ 数据库就绪")
    except Exception as e:
        print(f"⚠️ 建表异常: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(debug=False, host='0.0.0.0', port=port)
