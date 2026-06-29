import requests

# HN Algolia 搜索 API：无需 key、无需配置，永久免费。取当前热门 story。
URL = "https://hn.algolia.com/api/v1/search"


def fetch(limit=50):
    r = requests.get(URL, params={"tags": "story", "hitsPerPage": limit}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if "hits" not in body:
        raise RuntimeError(f"HN 返回异常: {str(body)[:200]}")
    out = []
    for h in body["hits"]:
        title = h.get("title")
        if not title:
            continue
        out.append({
            "source": "hackernews",
            "title": title,
            "raw_text": h.get("story_text") or "",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "signal": float(min(h.get("points", 0) or 0, 100)),
        })
    return out
