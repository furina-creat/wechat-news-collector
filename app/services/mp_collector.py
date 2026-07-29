"""
公众号文章采集器
---
通过搜狗微信搜索查找指定公众号的公开文章并入库。
"""

import re
import logging
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from app import db
from app.models import NewsArticle, WeChatMPAccount

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def search_articles(account_name, max_pages=2):
    """通过搜狗微信搜索公众号的文章。

    返回格式：[{"title":.., "url":.., "abstract":.., "source":.., "date":..}]
    """
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(1, max_pages + 1):
        url = (
            f"https://weixin.sogou.com/weixin"
            f"?type=2&s_from=input&query={account_name}&ie=utf8"
            f"&_sug_=n&_sug_type_=&page={page}"
        )
        try:
            resp = session.get(url, timeout=15)
            resp.encoding = "utf-8"
            html = resp.text
        except Exception as e:
            logger.warning(f"搜狗搜索第{page}页失败: {e}")
            continue

        soup = BeautifulSoup(html, "lxml")
        items = soup.select(".news-list2 .news-box")

        if not items:
            # 备用选择器
            items = soup.select(".wx-rb .wx-rb-item") or []
        if not items:
            logger.info(f"搜狗第{page}页无结果，可能被反爬")
            break

        for item in items:
            try:
                title_el = item.select_one("h3 a, .tit a, .wx-rb-title a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                article_url = title_el.get("href", "")
                if article_url and not article_url.startswith("http"):
                    article_url = "https://weixin.sogou.com" + article_url

                abstract_el = item.select_one(".txt-info, .wx-rb-abstract, p")
                abstract = abstract_el.get_text(strip=True) if abstract_el else ""

                # 来源（公众号名称）
                src_el = item.select_one(".account, .wx-rb-source, .s-p")
                source_name = account_name
                if src_el:
                    sn = src_el.get_text(strip=True)
                    if sn:
                        source_name = sn

                # 日期
                date_el = item.select_one(".time, .wx-rb-date, span.s2")
                date_str = date_el.get_text(strip=True) if date_el else ""

                if title and article_url:
                    results.append({
                        "title": title,
                        "url": article_url,
                        "abstract": abstract,
                        "source": source_name,
                        "date_str": date_str,
                    })
            except Exception as e:
                logger.debug(f"解析单条失败: {e}")

        time.sleep(1.5)  # 礼貌间隔

    return results


def fetch_article_content(url):
    """获取微信文章的正文内容。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        # 公众号文章正文
        content_el = soup.select_one("#js_content, .rich_media_content, article")
        if content_el:
            return content_el.get_text(strip=True)[:2000]
        # 备用
        for tag in ["div.content", "div.article", ".article-body"]:
            el = soup.select_one(tag)
            if el:
                return el.get_text(strip=True)[:2000]
        return ""
    except Exception as e:
        logger.warning(f"获取正文失败: {url[:50]} - {e}")
        return ""


def _auto_category(title, abstract):
    """自动判断分类。"""
    t = (title or "") + " " + (abstract or "")
    if any(k in t for k in ['考研', '考公', '公务员', '行测', '教育', '招生',
                              '研究生', '复试', '考点', '备考', '录取', '分数线',
                              '学位', '学历', '大学', '高校', '国考', '省考',
                              '申论', '事业单位', '教师招聘']):
        return '考公考研'
    if any(k in t for k in ['招聘', '求职', '面试', '简历', '职场', '就业',
                              '实习', 'offer', '校招', '薪水', '工资', '待遇',
                              '跳槽', '裁员', '猎头', '管培生', '应届生', '秋招']):
        return '应届求职'
    if any(k in t for k in ['股票', '股市', '大盘', '涨停', '跌停', '上证',
                              'A股', '港股', '基金', '投资', '行情', '板块']):
        return '股票市场'
    return '综合'


def crawl_account(account_id):
    """采集指定公众号的最新文章并入库。"""
    acct = WeChatMPAccount.query.get(account_id)
    if not acct or acct.status != '启用':
        return {"error": "账号不存在或已停用"}

    name = acct.name
    logger.info(f"开始采集公众号: {name}")

    articles = search_articles(name, max_pages=2)
    logger.info(f"搜到 {len(articles)} 篇")

    saved = 0
    skipped = 0
    for art in articles:
        # 检查是否已存在（同URL）
        existing = NewsArticle.query.filter_by(url=art["url"]).first()
        if existing:
            skipped += 1
            continue

        # 获取正文（只对前5篇获取完整内容，避免被 ban）
        content = ""
        if saved < 5:
            content = fetch_article_content(art["url"])

        cat = acct.category if acct.category != '综合' else _auto_category(
            art["title"], art.get("abstract", "")
        )

        article = NewsArticle(
            title=art["title"],
            content=content or art.get("abstract", ""),
            url=art["url"],
            source_site=f"公众号:{art.get('source', name)}",
            category=cat,
            collected_at=datetime.now(),
        )
        db.session.add(article)
        saved += 1

    db.session.commit()

    acct.last_crawl = datetime.now()
    acct.crawl_count = (acct.crawl_count or 0) + saved
    db.session.commit()

    # 限制文章总数
    total = NewsArticle.query.count()
    if total > 500:
        exceed = total - 500
        oldest = NewsArticle.query.order_by(NewsArticle.collected_at.asc()).limit(exceed).all()
        for o in oldest:
            db.session.delete(o)
        db.session.commit()

    return {"account": name, "found": len(articles), "saved": saved, "skipped": skipped}


def crawl_all_accounts():
    """采集所有启用账号。"""
    accounts = WeChatMPAccount.query.filter_by(status='启用').all()
    results = []
    for acct in accounts:
        try:
            r = crawl_account(acct.id)
            results.append(r)
        except Exception as e:
            logger.error(f"采集 [{acct.name}] 失败: {e}")
            results.append({"account": acct.name, "error": str(e)[:80]})
        time.sleep(2)
    return results
