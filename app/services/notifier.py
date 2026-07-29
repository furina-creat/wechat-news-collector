"""
通知服务
---
支持 QQ 邮箱 SMTP 发送邮件 + 微信机器人推送。
"""

import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局配置缓存（从环境变量读取，可在运行时通过 API 修改）
_config = {
    "email_enabled": False,
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_ssl": True,
    "email_from": "",
    "email_pass": "",  # QQ邮箱授权码
    "email_to": "",
    "wechat_enabled": False,
    "wechat_bridge_url": "http://127.0.0.1:8123",  # 本地 wechat-bridge API
    "notify_on_crawl": True,
    "notify_categories": ["考公考研", "应届求职", "股票市场"],
}


def get_config():
    return _config.copy()


def update_config(**kwargs):
    for k, v in kwargs.items():
        if k in _config:
            _config[k] = v
    return _config.copy()


def send_email(subject, body, to_addr=None):
    """通过 QQ 邮箱发送邮件。"""
    cfg = _config
    if not cfg["email_enabled"] or not cfg["email_from"] or not cfg["email_pass"]:
        return {"success": False, "error": "邮箱未配置"}

    to = to_addr or cfg["email_to"]
    if not to:
        return {"success": False, "error": "收件地址未设置"}

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = Header(cfg["email_from"], "utf-8")
        msg["To"] = Header(to, "utf-8")
        msg["Subject"] = Header(subject, "utf-8")

        if cfg["smtp_ssl"]:
            server = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
        else:
            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
            server.starttls()

        server.login(cfg["email_from"], cfg["email_pass"])
        server.sendmail(cfg["email_from"], [to], msg.as_string())
        server.quit()
        logger.info(f"邮件发送成功: {subject[:30]}")
        return {"success": True}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "SMTP 认证失败，请检查邮箱地址和授权码"}
    except smtplib.SMTPException as e:
        return {"success": False, "error": f"SMTP 错误: {str(e)[:80]}"}
    except Exception as e:
        return {"success": False, "error": str(e)[:80]}


def send_wechat_msg(text):
    """通过本地 wechat-bridge 发送微信消息（需要 bridge 在运行）。"""
    cfg = _config
    if not cfg["wechat_enabled"]:
        return {"success": False, "error": "微信推送未开启"}

    import urllib.request, json as _json
    try:
        payload = _json.dumps({
            "msg_id": f"sys-{int(datetime.now().timestamp())}",
            "from_user": "system",
            "text": text,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{cfg['wechat_bridge_url']}/api/respond",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
        logger.info("微信消息已推送")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"微信推送失败: {str(e)[:60]}"}


def notify_new_articles(articles, source_name="系统"):
    """通知新采集的文章。"""
    if not articles:
        return

    cfg = _config
    if not cfg["notify_on_crawl"]:
        return

    # 只推送关注的分类
    target_cats = set(cfg.get("notify_categories", []))
    matched = [a for a in articles if a.get("category") in target_cats]
    if not matched:
        return

    # 最多推送 5 篇
    matched = matched[:5]
    lines = [f"📰 新文章推送 ({source_name})", ""]
    for a in matched:
        cat = a.get("category", "综合")
        title = (a.get("title") or "")[:40]
        src = a.get("source_site") or a.get("source", "")
        lines.append(f"[{cat}] {title}")
        if src:
            lines.append(f"   来源: {src}")
    body = "\n".join(lines)

    # 邮件通知
    if cfg["email_enabled"]:
        threading.Thread(
            target=send_email,
            args=(f"📰 新文章推送 - {source_name}", body),
            daemon=True,
        ).start()

    # 微信通知
    if cfg["wechat_enabled"]:
        threading.Thread(
            target=send_wechat_msg,
            args=(body,),
            daemon=True,
        ).start()


def send_test_email():
    """发送测试邮件。"""
    return send_email(
        "✅ 通知服务测试",
        f"这是一封测试邮件\n\n如果你收到这封邮件，说明 QQ 邮箱配置正确！\n发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )
