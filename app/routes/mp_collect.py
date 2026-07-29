"""
公众号文章采集 - API 路由
---
管理关注的公众号列表，手动/自动采集文章。
"""

import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from app import db
from app.models import NewsArticle, WeChatMPAccount
from app.services.mp_collector import crawl_account, crawl_all_accounts

logger = logging.getLogger(__name__)

mp_collect_bp = Blueprint("mp_collect", __name__, url_prefix="/api/mp-collect")


# ---- 账号管理 ----

@mp_collect_bp.route("/accounts", methods=["GET"])
def list_accounts():
    accounts = WeChatMPAccount.query.order_by(WeChatMPAccount.created_at.desc()).all()
    return jsonify({
        "code": 200,
        "data": [{
            "id": a.id,
            "name": a.name,
            "wxid": a.wxid or "",
            "category": a.category,
            "status": a.status,
            "last_crawl": a.last_crawl.isoformat() if a.last_crawl else None,
            "crawl_count": a.crawl_count or 0,
        } for a in accounts],
    })


@mp_collect_bp.route("/accounts", methods=["POST"])
def add_account():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "请输入公众号名称"}), 400

    existing = WeChatMPAccount.query.filter_by(name=name).first()
    if existing:
        return jsonify({"code": 400, "message": f"「{name}」已在监控列表中"}), 400

    acct = WeChatMPAccount(
        name=name,
        wxid=data.get("wxid", ""),
        category=data.get("category", "综合"),
    )
    db.session.add(acct)
    db.session.commit()

    return jsonify({"code": 200, "message": f"已添加「{name}」", "data": {"id": acct.id}})


@mp_collect_bp.route("/accounts/<int:account_id>", methods=["DELETE"])
def delete_account(account_id):
    acct = WeChatMPAccount.query.get_or_404(account_id)
    db.session.delete(acct)
    db.session.commit()
    return jsonify({"code": 200, "message": f"已删除「{acct.name}」"})


@mp_collect_bp.route("/accounts/<int:account_id>/crawl", methods=["POST"])
def trigger_crawl(account_id):
    """手动触发采集指定公众号。"""
    try:
        result = crawl_account(account_id)
        if "error" in result:
            return jsonify({"code": 500, "message": result["error"]}), 500
        return jsonify({
            "code": 200,
            "message": f"采集完成: 新增 {result['saved']} 篇, 跳过 {result['skipped']} 篇",
            "data": result,
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"采集失败: {str(e)[:80]}"}), 500


@mp_collect_bp.route("/crawl-all", methods=["POST"])
def trigger_crawl_all():
    """采集所有启用的公众号。"""
    try:
        results = crawl_all_accounts()
        total_saved = sum(r.get("saved", 0) for r in results)
        total_found = sum(r.get("found", 0) for r in results)
        return jsonify({
            "code": 200,
            "message": f"全部采集完成: 共找到 {total_found} 篇, 新增 {total_saved} 篇",
            "data": results,
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"批量采集失败: {str(e)[:80]}"}), 500


# ---- 文章列表 ----

@mp_collect_bp.route("/articles", methods=["GET"])
def list_articles():
    """查看从公众号采集到的文章。"""
    account_name = request.args.get("account", "")
    page = int(request.args.get("page", 1))
    per_page = 20

    query = NewsArticle.query.filter(
        NewsArticle.source_site.ilike("公众号:%")
    )
    if account_name:
        query = query.filter(NewsArticle.source_site.ilike(f"%{account_name}%"))

    total = query.count()
    articles = query.order_by(NewsArticle.collected_at.desc()) \
                     .offset((page - 1) * per_page) \
                     .limit(per_page).all()

    return jsonify({
        "code": 200,
        "data": {
            "items": [{
                "id": a.id,
                "title": a.title,
                "content": (a.content or "")[:120],
                "source": a.source_site,
                "category": a.category,
                "url": a.url,
                "collected_at": a.collected_at.isoformat() if a.collected_at else None,
            } for a in articles],
            "total": total,
            "page": page,
        },
    })


@mp_collect_bp.route("/stats", methods=["GET"])
def stats():
    """公众号采集统计。"""
    accounts = WeChatMPAccount.query.count()
    articles = NewsArticle.query.filter(
        NewsArticle.source_site.ilike("公众号:%")
    ).count()
    return jsonify({
        "code": 200,
        "data": {
            "accounts": accounts,
            "articles": articles,
        },
    })
