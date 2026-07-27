import requests
from flask import current_app
from app.models import WechatUserInfo, db


class WechatService:
    
    @staticmethod
    def get_oauth_url(redirect_uri):
        """
        生成微信 OAuth 授权链接
        用户在浏览器打开这个链接，扫码后微信会跳转回 redirect_uri?code=xxx
        """
        appid = current_app.config['WECHAT_APP_ID']
        if not appid or 'your_' in appid:
            return None
        from urllib.parse import quote
        encoded_uri = quote(redirect_uri)
        url = ('https://open.weixin.qq.com/connect/qrconnect'
               f'?appid={appid}&redirect_uri={encoded_uri}'
               '&response_type=code&scope=snsapi_login&state=STATE#wechat_redirect')
        return url
    
    @staticmethod
    def get_user_info_by_code(code, redirect_uri=None):
        """
        通过微信登录code获取用户信息
        
        1. 如果 .env 中配置了 WECHAT_APP_ID 和 WECHAT_APP_SECRET → 调用真实微信 API
        2. 如果未配置 → 使用模拟数据（方便没有开放平台账号时测试）
        """
        appid = current_app.config['WECHAT_APP_ID']
        secret = current_app.config['WECHAT_APP_SECRET']
        
        # 没有配置真实凭证 → 使用模拟数据
        if not appid or not secret or 'your_' in appid:
            # 生成模拟数据（openid 基于当前时间，避免重复）
            import hashlib
            fake_openid = 'mock_' + hashlib.md5(code.encode()).hexdigest()[:16]
            
            mock_data = {
                'openid': fake_openid,
                'nickname': '微信用户_' + code[:4],
                'sex': 1,
                'province': '广东',
                'city': '深圳',
                'headimgurl': ''
            }
            
            info = WechatUserInfo.query.filter_by(openid=mock_data['openid']).first()
            if not info:
                info = WechatUserInfo(openid=mock_data['openid'])
            
            info.nickname = mock_data['nickname']
            info.gender = mock_data['sex']
            info.region = f"{mock_data['province']} {mock_data['city']}"
            info.avatar_url = mock_data['headimgurl']
            info.authorized_at = db.func.now()
            
            db.session.add(info)
            db.session.commit()
            
            return {
                'openid': info.openid,
                'nickname': info.nickname,
                'gender': info.gender,
                'region': info.region,
                'avatar_url': info.avatar_url,
                '_mock': True  # 标记为模拟数据
            }
        
        # 已配置真实凭证 → 调用微信真实 API
        try:
            # 第一步：用 code 换取 access_token 和 openid
            token_url = ('https://api.weixin.qq.com/sns/oauth2/access_token'
                        f'?appid={appid}&secret={secret}&code={code}&grant_type=authorization_code')
            token_resp = requests.get(token_url, timeout=10).json()
            
            if 'errcode' in token_resp:
                raise Exception(token_resp.get('errmsg', '微信API调用失败'))
            
            # 第二步：获取用户个人信息
            info_url = ('https://api.weixin.qq.com/sns/userinfo'
                       f'?access_token={token_resp["access_token"]}'
                       f'&openid={token_resp["openid"]}&lang=zh_CN')
            user_info = requests.get(info_url, timeout=10).json()
            
            if 'errcode' in user_info:
                raise Exception(user_info.get('errmsg', '获取用户信息失败'))
            
            # 存储或更新到数据库
            info = WechatUserInfo.query.filter_by(openid=user_info['openid']).first()
            if not info:
                info = WechatUserInfo(openid=user_info['openid'])
            
            info.nickname = user_info.get('nickname', '')
            info.gender = user_info.get('sex', 0)
            info.region = f"{user_info.get('province','')} {user_info.get('city','')}".strip()
            info.avatar_url = user_info.get('headimgurl', '')
            info.authorized_at = db.func.now()
            
            db.session.add(info)
            db.session.commit()
            
            return {
                'openid': info.openid,
                'nickname': info.nickname,
                'gender': info.gender,
                'region': info.region,
                'avatar_url': info.avatar_url,
                '_mock': False
            }
            
        except requests.exceptions.Timeout:
            raise Exception('微信API请求超时，请稍后重试')
        except requests.exceptions.ConnectionError:
            raise Exception('无法连接到微信服务器，请检查网络')
        except Exception as e:
            raise Exception(f'微信授权失败: {str(e)}') 
