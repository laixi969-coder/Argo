from __future__ import annotations

from datetime import datetime, timezone

import requests

from src import config

# 小红书需求搜索（走 TikHub）：中文消费与工具需求最密集的场域。
# 「求推荐 / 有偿求 / 有没有」帖是用户主动张口要解法，天然的需求表达证据；
# 「平替」帖暴露价格敏感点与现有方案的溢价空间。
_KEYWORDS = (
    "求推荐 工具",
    "求推荐 软件",
    "有偿求助",
    "有没有什么办法",
    "平替 好用",
)
_TIME_FILTER = "一周内"  # 需求雷达只看新鲜表达，旧帖交给历史去重


def _headers():
    return {"Authorization": f"Bearer {config.get('TIKHUB_API_KEY')}"}


def _base():
    url = config.get("TIKHUB_BASE_URL") or "https://api.tikhub.io"
    return url.rstrip("/")


def _search_notes(keyword: str) -> list[dict]:
    r = requests.get(
        f"{_base()}/api/v1/xiaohongshu/app_v2/search_notes",
        headers=_headers(),
        params={"keyword": keyword, "page": 1, "time_filter": _TIME_FILTER},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(
            f"TikHub 小红书搜索失败({keyword!r}): "
            + (body.get("message_zh") or body.get("message") or str(body)[:200])
        )
    inner = (body.get("data") or {}).get("data") or {}
    return inner.get("items") or []


def _to_opportunity(item: dict) -> dict | None:
    note = item.get("note") or {}
    note_id = note.get("id")
    title = (note.get("title") or "").strip()
    desc = (note.get("desc") or "").strip()
    if not note_id or not (title or desc):
        return None
    liked = int(note.get("liked_count") or 0)
    comments = int(note.get("comments_count") or 0)
    # 求助帖赞少评多：评论区就是候选解法与共鸣，权重高于点赞
    signal = float(min(liked + comments * 2, 100))
    ts = note.get("timestamp")
    published = (
        datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
    )
    return {
        "source": "xhs",
        "title": title or desc[:80],
        "raw_text": desc,
        "url": f"https://www.xiaohongshu.com/explore/{note_id}",
        "signal": signal,
        "opportunity_type": "需求信号",
        "is_outcome": False,
        "published_at": published,
    }


def fetch() -> list[dict]:
    if not config.get("TIKHUB_API_KEY"):
        raise RuntimeError("TikHub API Key 未配置（可选源，跳过）")
    out, seen = [], set()
    for kw in _KEYWORDS:
        try:
            items = _search_notes(kw)
        except Exception as exc:  # 单关键词失败不拖垮整源
            print(f"[xhs] 关键词 {kw!r} 失败: {exc}")
            continue
        for item in items:
            o = _to_opportunity(item)
            if o and o["url"] not in seen:
                seen.add(o["url"])
                out.append(o)
    return out
