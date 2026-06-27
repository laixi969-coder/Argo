import requests
from src import config

# 抓「有人表达需求/愿意掏钱」的视频描述，当作产品机会信号
KEYWORDS = [
    "I wish there was an app",
    "why is there no app",
    "someone should make",
    "I would pay for",
    "nobody has made",
    "there should be an app",
]

_PER_KEYWORD = 10  # 每个关键词抓多少条，控制 credit 消耗


def _headers():
    return {
        "Authorization": f"Bearer {config.get('TIKHUB_API_KEY')}",
        "Content-Type": "application/json",
    }


def _base():
    url = config.get("TIKHUB_BASE_URL") or "https://api.tikhub.io"
    return url.rstrip("/")


def _search_keyword(keyword: str, count: int = _PER_KEYWORD) -> list[dict]:
    """搜索单个关键词，返回统一格式的 post 列表。"""
    r = requests.get(
        f"{_base()}/api/v1/tiktok/app/v3/fetch_general_search_result",
        headers=_headers(),
        params={"keyword": keyword, "count": count, "offset": 0},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(
            f"TikHub 搜索失败({keyword!r}): "
            + (body.get("message_zh") or body.get("message") or str(body)[:200])
        )

    items = []
    for item in body.get("data", {}).get("data", []):
        aweme = item.get("aweme_info") or item  # 结构因版本略有不同
        desc = aweme.get("desc", "").strip()
        if not desc:
            continue
        stats = aweme.get("statistics") or {}
        digg = stats.get("digg_count", 0) or 0
        play = stats.get("play_count", 0) or 0
        signal = float(min(max(digg, play // 100), 100))  # 归一化到 0-100

        share_url = (
            aweme.get("share_url")
            or f"https://www.tiktok.com/@{aweme.get('author', {}).get('unique_id', '')}"
            f"/video/{aweme.get('aweme_id', '')}"
        )

        items.append({
            "source": "tiktok",
            "title": desc[:80],
            "raw_text": desc,
            "url": share_url,
            "signal": signal,
        })
    return items


def fetch() -> list[dict]:
    if not config.get("TIKHUB_API_KEY"):
        raise RuntimeError("TikHub API Key 未配置（可选源，跳过）")

    out, seen = [], set()
    for kw in KEYWORDS:
        try:
            posts = _search_keyword(kw)
        except Exception as exc:
            print(f"[tikhub] 关键词 {kw!r} 失败: {exc}")
            continue
        for p in posts:
            if p["url"] not in seen:
                seen.add(p["url"])
                out.append(p)

    return out
