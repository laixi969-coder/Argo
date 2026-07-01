import requests

from src.sources.demand_keywords import KEYWORDS  # 跨平台共用需求词库

# HN Algolia 搜索 API：无需 key、无需配置，永久免费。
# 按需求关键词搜，而非拉全站热榜——热榜是新闻，含不了「有人要买什么」的需求。
URL = "https://hn.algolia.com/api/v1/search"
_PER_KEYWORD = 15
_FRONT_PAGE_COUNT = 30
_PRODUCT_POOL_COUNT = 50


def _query(**params):
    r = requests.get(URL, params=params, timeout=30)
    r.raise_for_status()
    body = r.json()
    if "hits" not in body:
        raise RuntimeError(f"HN 返回异常: {str(body)[:200]}")
    return body["hits"]


def _search(keyword, count=_PER_KEYWORD):
    return _query(query=keyword, tags="story", hitsPerPage=count)


def _front_page():
    """HN 当天持续更新的首页内容。"""
    return _query(tags="front_page", hitsPerPage=_FRONT_PAGE_COUNT)


def _product_pool():
    """不限发布日期的 Show HN 成果产品池，以采用度信号过滤纯练手项目。"""
    # HN Algolia 不允许对 points 做服务端 numericFilters，先取较大的历史
    # Show HN 候选集，再在本地按采用度过滤和排序。
    hits = _query(
        query="Show HN:",
        tags="story",
        restrictSearchableAttributes="title",
        hitsPerPage=200,
    )
    products = [
        h for h in hits
        if str(h.get("title", "")).lower().startswith("show hn:")
        and (h.get("points", 0) or 0) >= 20
    ]
    products.sort(key=lambda h: h.get("points", 0) or 0, reverse=True)
    return products[:_PRODUCT_POOL_COUNT]


def fetch():
    out, seen = [], set()
    groups = []
    for kw in KEYWORDS:
        try:
            hits = _search(kw)
        except Exception as exc:  # 单关键词失败不拖垮整源
            print(f"[hackernews] 关键词 {kw!r} 失败: {exc}")
            continue
        groups.append((hits, "需求信号"))
    for label, loader in (("今日内容", _front_page), ("已有成果产品", _product_pool)):
        try:
            groups.append((loader(), label))
        except Exception as exc:
            print(f"[hackernews] {label}抓取失败: {exc}")
    for hits, opportunity_type in groups:
        for h in hits:
            title = h.get("title")
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            if not title or url in seen:
                continue
            seen.add(url)
            item_type = ("已有成果产品"
                         if str(title).lower().startswith("show hn:")
                         else opportunity_type)
            out.append({
                "source": "hackernews",
                "title": title,
                "raw_text": h.get("story_text") or "",
                "url": url,
                "signal": float(min(h.get("points", 0) or 0, 100)),
                "opportunity_type": item_type,
                "published_at": h.get("created_at") or "",
            })
    return out
