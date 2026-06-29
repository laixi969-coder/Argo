import requests

from src.sources.demand_keywords import KEYWORDS  # 跨平台共用需求词库

# HN Algolia 搜索 API：无需 key、无需配置，永久免费。
# 按需求关键词搜，而非拉全站热榜——热榜是新闻，含不了「有人要买什么」的需求。
URL = "https://hn.algolia.com/api/v1/search"
_PER_KEYWORD = 15


def _search(keyword, count=_PER_KEYWORD):
    r = requests.get(
        URL,
        params={"query": keyword, "tags": "story", "hitsPerPage": count},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if "hits" not in body:
        raise RuntimeError(f"HN 返回异常: {str(body)[:200]}")
    return body["hits"]


def fetch():
    out, seen = [], set()
    for kw in KEYWORDS:
        try:
            hits = _search(kw)
        except Exception as exc:  # 单关键词失败不拖垮整源
            print(f"[hackernews] 关键词 {kw!r} 失败: {exc}")
            continue
        for h in hits:
            title = h.get("title")
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            if not title or url in seen:
                continue
            seen.add(url)
            out.append({
                "source": "hackernews",
                "title": title,
                "raw_text": h.get("story_text") or "",
                "url": url,
                "signal": float(min(h.get("points", 0) or 0, 100)),
            })
    return out
