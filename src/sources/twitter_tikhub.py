"""Twitter/X 机会源（经 TikHub）。

用需求词库在 Twitter 搜推文，提炼产品机会信号。不需要 Twitter 官方 key，
走 TikHub 的 twitter/web/fetch_search_timeline 接口。返回字段与其它源统一：
{source, title, raw_text, url, signal}。
"""
import requests

from src import config
from src.sources.demand_keywords import KEYWORDS

_PER_KEYWORD = 15  # 每个关键词取多少条，控制 TikHub credit 消耗
_ENDPOINT = "/api/v1/twitter/web/fetch_search_timeline"


def _headers():
    return {"Authorization": f"Bearer {config.get('TIKHUB_API_KEY')}"}


def _base():
    return (config.get("TIKHUB_BASE_URL") or "https://api.tikhub.io").rstrip("/")


def _to_int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _extract_tweets(body: dict) -> list[dict]:
    """从 data.timeline 归一化推文。"""
    timeline = (body.get("data") or {}).get("timeline") or []
    out, seen = [], set()
    for t in timeline:
        if not isinstance(t, dict):
            continue
        text = (t.get("text") or "").strip()
        tid = t.get("tweet_id") or t.get("id_str")
        screen = t.get("screen_name") or ""
        if not text or not tid:
            continue
        url = f"https://x.com/{screen}/status/{tid}" if screen else f"https://x.com/i/status/{tid}"
        if url in seen:
            continue
        seen.add(url)

        signal = float(min(
            _to_int(t.get("favorites")) + _to_int(t.get("retweets")) + _to_int(t.get("replies")),
            100,
        ))
        out.append({
            "source": "twitter",
            "title": text[:80],
            "raw_text": (f"@{screen}: " if screen else "") + text,
            "url": url,
            "signal": signal,
        })
    return out


def _search(keyword: str, count: int = _PER_KEYWORD) -> list[dict]:
    r = requests.get(
        f"{_base()}{_ENDPOINT}",
        headers=_headers(),
        params={"keyword": keyword, "search_type": "Top"},
        timeout=40,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(
            f"TikHub Twitter 搜索失败({keyword!r}): "
            + (body.get("message_zh") or body.get("message") or str(body)[:200])
        )
    return _extract_tweets(body)[:count]


def fetch() -> list[dict]:
    if not config.get("TIKHUB_API_KEY"):
        raise RuntimeError("TikHub API Key 未配置（可选源，跳过）")

    out, seen = [], set()
    for kw in KEYWORDS:
        try:
            tweets = _search(kw)
        except Exception as exc:  # 单关键词失败不拖垮整源
            print(f"[twitter_tikhub] 关键词 {kw!r} 失败: {exc}")
            continue
        for t in tweets:
            if t["url"] not in seen:
                seen.add(t["url"])
                out.append(t)
    return out
