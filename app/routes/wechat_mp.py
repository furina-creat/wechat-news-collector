"""
微信公众号消息 Webhook
---
接收粉丝消息，自动回复。
URL（公众号后台配置）：https://你的域名/wechat/mp
"""

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET

from flask import Blueprint, request, make_response, jsonify
from app import db

logger = logging.getLogger(__name__)

wechat_mp_bp = Blueprint("wechat_mp", __name__, url_prefix="/wechat")


# ---------------------------------------------------------------------------
# 签名验证
# ---------------------------------------------------------------------------

def check_signature(token, signature, timestamp, nonce):
    parts = sorted([token, timestamp, nonce])
    return hashlib.sha1("".join(parts).encode()).hexdigest() == signature


# ---------------------------------------------------------------------------
# XML 消息解析
# ---------------------------------------------------------------------------

def _snake(tag):
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", tag)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def parse_xml(xml_body):
    root = ET.fromstring(xml_body)
    raw = {}
    for child in root:
        raw[_snake(child.tag)] = (child.text or "").strip()

    msg = {
        "to_user": raw.get("to_user_name", ""),
        "from_user": raw.get("from_user_name", ""),
        "create_time": int(raw.get("create_time", 0)),
        "msg_type": raw.get("msg_type", ""),
        "msg_id": raw.get("msg_id", ""),
    }

    t = msg["msg_type"]
    if t == "text":
        msg["content"] = raw.get("content", "")
    elif t == "image":
        msg["pic_url"] = raw.get("pic_url", "")
        msg["media_id"] = raw.get("media_id", "")
    elif t == "voice":
        msg["media_id"] = raw.get("media_id", "")
        msg["recognition"] = raw.get("recognition", "")
    elif t == "event":
        msg["event"] = raw.get("event", "")
        msg["event_key"] = raw.get("event_key", "")
    elif t == "location":
        msg["label"] = raw.get("label", "")
    elif t == "link":
        msg["title"] = raw.get("title", "")
        msg["url"] = raw.get("url", "")
    return msg


# ---------------------------------------------------------------------------
# 回复 XML 生成
# ---------------------------------------------------------------------------

def _cdata(text):
    return f"<![CDATA[{text}]]>"


def text_reply(to_user, from_user, content):
    ts = int(time.time())
    return (
        f"<xml>\n"
        f"<ToUserName>{_cdata(to_user)}</ToUserName>\n"
        f"<FromUserName>{_cdata(from_user)}</FromUserName>\n"
        f"<CreateTime>{ts}</CreateTime>\n"
        f"<MsgType>{_cdata('text')}</MsgType>\n"
        f"<Content>{_cdata(content)}</Content>\n"
        f"</xml>"
    )


def success_reply():
    return "success"


# ---------------------------------------------------------------------------
# 关键词 + 数据库回复引擎
# ---------------------------------------------------------------------------

_STATIC_REPLIES = {
    "help": (
        "欢迎！我可以帮你：\n"
        "1. 搜索最新新闻资讯\n"
        "2. 查询考研、考公信息\n"
        "3. 查看求职招聘动态\n"
        "4. 了解股票市场行情\n\n"
        "直接发关键词试试，比如「考研」「国考」「秋招」"
    ),
    "subscribe": "感谢关注！🎉 我是智能新闻助手，发送「帮助」查看我能做什么。",
    "about": "我是新闻采集系统的公众号助手，帮你搜索各类新闻资讯。",
    "default": "收到你的消息了！发送「帮助」查看我能做什么。",
}

_KEYWORD_ROUTES = {
    "help": ["帮助", "help", "菜单", "功能", "怎么用"],
    "about": ["关于", "你是谁", "介绍"],
}


def _match_keyword(content):
    c = content.strip().lower()
    for route, keywords in _KEYWORD_ROUTES.items():
        if any(kw in c for kw in keywords):
            return route
    return None


def _search_articles(content):
    """在新闻数据库中搜索相关文章。"""
    from app.models import NewsArticle
    try:
        keyword = content.strip()[:30]
        articles = (
            NewsArticle.query
            .filter(
                db.or_(
                    NewsArticle.title.ilike(f"%{keyword}%"),
                    NewsArticle.content.ilike(f"%{keyword}%"),
                )
            )
            .order_by(NewsArticle.collected_at.desc())
            .limit(3)
            .all()
        )
        if not articles:
            return None
        lines = []
        for a in articles:
            src = a.source_site or "未知"
            cat = a.category or "综合"
            lines.append(f"📰 {a.title[:40]}\n  来源: {src} | 分类: {cat}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.warning(f"搜索文章失败: {e}")
        return None


def _generate_reply(msg):
    content = (msg.get("content") or "").strip()
    msg_type = msg.get("msg_type", "")
    event = msg.get("event", "")

    if msg_type == "event":
        if event == "subscribe":
            return _STATIC_REPLIES["subscribe"]
        elif event == "unsubscribe":
            return None
        elif event == "CLICK":
            return f"你点击了「{msg.get('event_key', '')}」按钮"
        return None

    if msg_type == "image":
        return "图片已收到！你可以继续给我发文字消息。"
    if msg_type == "voice":
        rec = msg.get("recognition", "")
        if rec:
            msg["msg_type"] = "text"
            msg["content"] = rec
            return _generate_reply(msg)
        return "语音已收到，但我暂时还不能处理没有识别结果的语音。"
    if msg_type == "location":
        return f"收到你的位置：{msg.get('label', '未知')}。有什么需要帮忙的吗？"
    if msg_type == "link":
        return f"收到你分享的文章：《{msg.get('title', '无标题')}》。"

    if msg_type != "text" or not content:
        return _STATIC_REPLIES["default"]

    route = _match_keyword(content)
    if route and route in _STATIC_REPLIES:
        return _STATIC_REPLIES[route]

    result = _search_articles(content)
    if result:
        return f"为你找到以下相关文章：\n\n{result}"

    return _STATIC_REPLIES["default"]


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@wechat_mp_bp.route("/mp", methods=["GET", "POST"])
def webhook():
    """微信服务器回调入口。"""
    from flask import current_app as app

    token = app.config.get("WECHAT_MP_TOKEN", "")
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    echostr = request.args.get("echostr", "")

    if not check_signature(token, signature, timestamp, nonce):
        logger.warning("签名验证失败")
        return "invalid signature", 403

    if request.method == "GET":
        logger.info("公众号 URL 验证通过")
        return echostr, 200, {"Content-Type": "text/plain"}

    xml_body = request.data.decode("utf-8")
    logger.debug(f"收到 XML: {xml_body[:200]}")

    try:
        msg = parse_xml(xml_body)
    except Exception as e:
        logger.error(f"解析 XML 失败: {e}")
        return success_reply()

    logger.info(
        f"[{msg.get('msg_type','?')}] "
        f"{msg.get('from_user','?')[:12]} → "
        f"{msg.get('content','') or msg.get('event','')}"
    )

    reply_text = _generate_reply(msg)

    if reply_text:
        xml_reply = text_reply(
            to_user=msg.get("from_user", ""),
            from_user=msg.get("to_user", ""),
            content=reply_text,
        )
        resp = make_response(xml_reply)
        resp.headers["Content-Type"] = "application/xml; charset=utf-8"
        return resp

    return success_reply()


@wechat_mp_bp.route("/mp/status")
def mp_status():
    from flask import current_app as app
    cfg = {
        "token_set": bool(app.config.get("WECHAT_MP_TOKEN")),
        "endpoint": "/wechat/mp",
    }
    return jsonify(cfg)
