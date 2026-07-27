from flask import Blueprint, request
from app.utils.response import success, error
from app.services.wechat_service import WechatService
from flask import current_app

wechat_bp = Blueprint('wechat', __name__)


@wechat_bp.route('/oauth_url', methods=['GET'])
def get_oauth_url():
    """获取微信 OAuth 授权链接"""
    redirect_uri = request.args.get('redirect_uri', 'http://localhost:5050')
    url = WechatService.get_oauth_url(redirect_uri)
    
    appid = current_app.config['WECHAT_APP_ID']
    
    secret = current_app.config['WECHAT_APP_SECRET']
    configured = bool(appid and secret and 'your_' not in appid and 'your_' not in secret)
    return success({
        'oauth_url': url,
        'is_configured': configured,
        'message': '已配置微信开放平台' if configured else '未配置微信开放平台，使用模拟模式'
    })


@wechat_bp.route('/auth', methods=['POST'])
def auth_wechat():
    """微信授权并获取用户信息"""
    code = request.json.get('code')
    if not code:
        return error('缺少授权code')
    try:
        data = WechatService.get_user_info_by_code(code)
        return success(data, '获取微信信息成功')
    except ValueError as e:
        return error(str(e), 400)
    except Exception as e:
        return error(f'微信接口调用失败: {str(e)}', 500)
