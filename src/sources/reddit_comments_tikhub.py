"""Reddit 评论区机会源（经 TikHub）。

用痛点词库搜 Reddit 评论，挖"骂出来的痛"。与 reddit_tikhub（搜帖子）互补。
走 fetch_dynamic_search 的 search_type=comment。归一化为统一格式
{source, title, raw_text, url, signal}。评论搜索精度一般，靠下游 /req 打分过滤。
"""
import time

import requests

from src import config
from src.sources.pain_keywords import KEYWORDS

_PER_KEYWORD = 8  # 评论噪音大，每词少取，控量 + 控 credit
_ENDPOINT = "/api/v1/reddit/app/fetch_dynamic_search"


def _headers():
    return {"Authorization": f"Bearer {config.get('TIKHUB_API_KEY')}"}


def _base():
    return (config.get("TIKHUB_BASE_URL") or "https://api.tikhub.io").rstrip("/")


def _comment_url(comment_id: str, post_id: str) -> str:
    c = (comment_id or "").removeprefix("t1_")
    p = (post_id or "").removeprefix("t3_")
    if c and p:
        return f"https://www.reddit.com/comments/{p}/comment/{c}/"
    return ""


def _extract_comments(body: dict) -> list[dict]:
    """递归捞出含正文 + 父帖信息的评论对象，归一化。"""
    found = []

    def walk(x):
        if isinstance(x, dict):
            content = x.get("content")
            if isinstance(content, dict) and content.get("markdown") and isinstance(x.get("postInfo"), dict):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(body.get("data") or {})

    out, seen = [], set()
    for c in found:
        text = (c["content"].get("markdown") or "").strip()
        post = c["postInfo"]
        url = _comment_url(c.get("id", ""), post.get("id", ""))
        if not text or not url or url in seen:
            continue
        seen.add(url)

        sub = post.get("subreddit")
        prefixed = sub.get("prefixedName", "") if isinstance(sub, dict) else ""
        post_title = (post.get("title") or "").strip()
        signal = float(min(c.get("score") or 0, 100))

        ctx = f"[{prefixed} 评论"
        if post_title:
            ctx += f" · 帖:{post_title[:60]}"
        ctx += "] " + text

        out.append({
            "source": "reddit_comment",
            "title": text[:80],
            "raw_text": ctx,
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
            "search_type": "comment",
            "sort": "RELEVANCE",
            "time_range": "year",
            "need_format": "true",
        },
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(
            f"TikHub Reddit 评论搜索失败({keyword!r}): "
            + (body.get("message_zh") or body.get("message") or str(body)[:200])
        )
    return _extract_comments(body)[:count]


def fetch() -> list[dict]:
    if not config.get("TIKHUB_API_KEY"):
        raise RuntimeError("TikHub API Key 未配置（可选源，跳过）")

    out, seen = [], set()
    for kw in KEYWORDS:
        time.sleep(0.4)  # 关键词间轻节流，降低 TikHub 限流(400)
        try:
            comments = _search(kw)
        except Exception as exc:  # 单关键词失败不拖垮整源
            print(f"[reddit_comments_tikhub] 关键词 {kw!r} 失败: {exc}")
            continue
        for c in comments:
            if c["url"] not in seen:
                seen.add(c["url"])
                out.append(c)
    return out
