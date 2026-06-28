"""Reddit 机会源（经 TikHub）。

用需求词库在 Reddit 搜帖子，提炼成产品机会信号。不需要 Reddit 官方 key，
走 TikHub 的 reddit/app/fetch_dynamic_search 接口。返回字段与其它源统一：
{source, title, raw_text, url, signal}。
"""
import time

import requests

from src import config
from src.sources.demand_keywords import KEYWORDS

_PER_KEYWORD = 15  # 每个关键词取多少帖，控制 TikHub credit 消耗
_ENDPOINT = "/api/v1/reddit/app/fetch_dynamic_search"


def _headers():
    return {"Authorization": f"Bearer {config.get('TIKHUB_API_KEY')}"}


def _base():
    return (config.get("TIKHUB_BASE_URL") or "https://api.tikhub.io").rstrip("/")


def _extract_posts(body: dict) -> list[dict]:
    """从 TikHub 的 Reddit 组件流里递归捞出帖子对象，归一化。

    帖子在 data.search.dynamic.components.main.edges[].node.children[].post，
    但结构会随版本变，故递归找含 postTitle + 链接的对象，抗结构漂移。
    """
    found: list[dict] = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("postTitle") and (x.get("permalink") or x.get("url")):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(body.get("data") or {})

    out, seen = [], set()
    for p in found:
        permalink = p.get("permalink") or ""
        url = p.get("url") or (f"https://www.reddit.com{permalink}" if permalink else "")
        if not url or url in seen:
            continue
        seen.add(url)

        title = (p.get("postTitle") or "").strip()
        content = p.get("content")
        markdown = content.get("markdown", "").strip() if isinstance(content, dict) else ""
        sub = p.get("subreddit")
        prefixed = sub.get("prefixedName", "") if isinstance(sub, dict) else ""

        score = p.get("score") or 0
        comments = p.get("commentCount") or 0
        signal = float(min(score + comments, 100))

        body_text = (f"[{prefixed}] " if prefixed else "") + title
        if markdown:
            body_text += "\n" + markdown

        out.append({
            "source": "reddit",
            "title": (title or markdown)[:80],
            "raw_text": body_text,
            "url": url,
            "signal": signal,
        })
    return out


def _search(keyword: str, count: int = _PER_KEYWORD) -> list[dict]:
    r = requests.get(
        f"{_base()}{_ENDPOINT}",
        headers=_headers(),
        params={
            "query": keyword,
            "search_type": "post",
            "sort": "RELEVANCE",
            "time_range": "year",
            "need_format": "true",
        },
        timeout=40,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(
            f"TikHub Reddit 搜索失败({keyword!r}): "
            + (body.get("message_zh") or body.get("message") or str(body)[:200])
        )
    return _extract_posts(body)[:count]


def fetch() -> list[dict]:
    if not config.get("TIKHUB_API_KEY"):
        raise RuntimeError("TikHub API Key 未配置（可选源，跳过）")

    out, seen = [], set()
    for kw in KEYWORDS:
        time.sleep(0.4)  # 关键词间轻节流，从源头降低 TikHub 限流(400)
        try:
            posts = _search(kw)
        except Exception as exc:  # 单关键词失败不拖垮整源
            print(f"[reddit_tikhub] 关键词 {kw!r} 失败: {exc}")
            continue
        for p in posts:
            if p["url"] not in seen:
                seen.add(p["url"])
                out.append(p)
    return out
