from flask import Blueprint, request, session, jsonify
from app import db
from app.models import User
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def validate_email(email):
    return re.match(r'^[\w.+-]+@[\w-]+\.[\w.]+$', email)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    nickname = (data.get('nickname') or email.split('@')[0]).strip()
    
    if not email or not password:
        return jsonify({'code': 400, 'message': '邮箱和密码不能为空'}), 400
    if len(password) < 6:
        return jsonify({'code': 400, 'message': '密码至少6位'}), 400
    if not validate_email(email):
        return jsonify({'code': 400, 'message': '邮箱格式不正确'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'code': 400, 'message': '该邮箱已注册'}), 400
    
    user = User(email=email, nickname=nickname)
    user.set_password(password)
    user.last_login = datetime.now()
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    session['email'] = user.email
    session['nickname'] = user.nickname
    
    return jsonify({'code': 200, 'message': '注册成功', 'data': {
        'id': user.id, 'email': user.email, 'nickname': user.nickname
    }})

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    
    if not email or not password:
        return jsonify({'code': 400, 'message': '邮箱和密码不能为空'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'code': 401, 'message': '邮箱或密码错误'}), 401
    
    user.last_login = datetime.now()
    db.session.commit()
    
    session['user_id'] = user.id
    session['email'] = user.email
    session['nickname'] = user.nickname
    
    return jsonify({'code': 200, 'message': '登录成功', 'data': {
        'id': user.id, 'email': user.email, 'nickname': user.nickname
    }})

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'code': 200, 'message': '已退出登录'})


@auth_bp.route('/wechat/oauth_url', methods=['GET'])
def wechat_oauth_url():
    """获取微信绑定授权链接"""
    from app.services.wechat_service import WechatService
    from flask import current_app
    
    appid = current_app.config.get('WECHAT_APP_ID', '')
    if not appid or 'your_' in appid:
        return jsonify({'code': 200, 'data': {
            'is_configured': False,
            'message': '未配置微信开放平台，请在 .env 中填入 WECHAT_APP_ID 和 WECHAT_APP_SECRET'
        }})
    
    redirect_uri = request.args.get('redirect_uri', 'http://localhost:5050')
    url = WechatService.get_oauth_url(redirect_uri)
    return jsonify({'code': 200, 'data': {
        'oauth_url': url,
        'is_configured': True,
        'message': '已配置微信开放平台'
    }})

@auth_bp.route('/bind_wechat', methods=['POST'])
def bind_wechat():
    """绑定微信到当前用户"""
    if 'user_id' not in session:
        return jsonify({'code': 401, 'message': '请先登录'}), 401
    
    from app.services.wechat_service import WechatService
    from flask import current_app
    
    code = request.json.get('code')
    if not code:
        return jsonify({'code': 400, 'message': '缺少授权code'}), 400
    
    try:
        data = WechatService.get_user_info_by_code(code)
        user = User.query.get(session['user_id'])
        
        # Check if this WeChat is already bound to another user
        existing = User.query.filter_by(wechat_openid=data['openid']).first()
        if existing and existing.id != user.id:
            return jsonify({'code': 400, 'message': '该微信已被其他账号绑定'}), 400
        
        user.wechat_openid = data['openid']
        user.wechat_nickname = data.get('nickname', '')
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '微信绑定成功', 'data': {
            'wechat_nickname': user.wechat_nickname,
            'is_mock': data.get('_mock', False)
        }})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'绑定失败: {str(e)}'}), 500

@auth_bp.route('/unbind_wechat', methods=['POST'])
def unbind_wechat():
    """解绑微信"""
    if 'user_id' not in session:
        return jsonify({'code': 401, 'message': '请先登录'}), 401
    
    user = User.query.get(session['user_id'])
    user.wechat_openid = None
    user.wechat_nickname = ''
    db.session.commit()
    
    return jsonify({'code': 200, 'message': '微信已解绑'})

@auth_bp.route('/me', methods=['GET'])

def me():
    if 'user_id' not in session:
        return jsonify({'code': 401, 'message': '未登录'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'code': 401, 'message': '用户不存在'}), 401
    return jsonify({'code': 200, 'data': {
        'id': user.id, 'email': user.email,
        'nickname': user.nickname, 'avatar_url': user.avatar_url,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }})
