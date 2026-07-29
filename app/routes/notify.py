"""
通知设置 API
---
邮箱配置、推送测试、通知规则。
"""

import logging
from flask import Blueprint, request, jsonify

from app.services.notifier import (
    get_config, update_config, send_test_email,
    send_email, send_wechat_msg,
)

logger = logging.getLogger(__name__)

notify_bp = Blueprint("notify", __name__, url_prefix="/api/notify")


@notify_bp.route("/config", methods=["GET"])
def get_notify_config():
    """获取通知配置（脱敏）。"""
    cfg = get_config()
    return jsonify({
        "code": 200,
        "data": {
            "email_enabled": cfg["email_enabled"],
            "smtp_host": cfg["smtp_host"],
            "smtp_port": cfg["smtp_port"],
            "email_from": cfg["email_from"][:3] + "***@" + cfg["email_from"].split("@")[-1]
                         if "@" in cfg["email_from"] else "",
            "email_to": cfg["email_to"][:3] + "***" if cfg["email_to"] else "",
            "has_password": bool(cfg["email_pass"]),
            "wechat_enabled": cfg["wechat_enabled"],
            "notify_on_crawl": cfg["notify_on_crawl"],
            "notify_categories": cfg["notify_categories"],
        },
    })


@notify_bp.route("/config", methods=["POST"])
def set_notify_config():
    """更新通知配置。"""
    data = request.json or {}
    # 可更新的字段映射
    fields = {
        "email_enabled": bool,
        "smtp_host": str,
        "smtp_port": int,
        "email_from": str,
        "email_pass": str,
        "email_to": str,
        "wechat_enabled": bool,
        "wechat_bridge_url": str,
        "notify_on_crawl": bool,
        "notify_categories": list,
    }
    kwargs = {}
    for key, typ in fields.items():
        if key in data:
            val = data[key]
            if key == "notify_categories":
                kwargs[key] = val if isinstance(val, list) else []
            else:
                try:
                    kwargs[key] = typ(val)
                except (ValueError, TypeError):
                    pass

    update_config(**kwargs)
    return jsonify({"code": 200, "message": "配置已更新"})


@notify_bp.route("/test/email", methods=["POST"])
def test_email():
    """发送测试邮件。"""
    result = send_test_email()
    if result["success"]:
        return jsonify({"code": 200, "message": "测试邮件已发送，请检查收件箱"})
    return jsonify({"code": 500, "message": result.get("error", "发送失败")}), 500


@notify_bp.route("/test/wechat", methods=["POST"])
def test_wechat():
    """发送测试微信消息。"""
    result = send_wechat_msg("🔔 通知服务测试\n\n如果你收到这条消息，说明微信推送配置正确！")
    if result["success"]:
        return jsonify({"code": 200, "message": "测试消息已发送"})
    return jsonify({"code": 500, "message": result.get("error", "发送失败")}), 500


@notify_bp.route("/send", methods=["POST"])
def manual_notify():
    """手动发送通知。"""
    data = request.json or {}
    title = (data.get("title") or "通知").strip()
    content = (data.get("content") or "").strip()
    channels = data.get("channels", ["email"])  # email, wechat

    results = {}
    if "email" in channels:
        r = send_email(title, content)
        results["email"] = r
    if "wechat" in channels:
        r = send_wechat_msg(f"{title}\n\n{content}")
        results["wechat"] = r

    return jsonify({"code": 200, "data": results})
