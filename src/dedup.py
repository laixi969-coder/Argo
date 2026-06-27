"""跨天去重：优先推没推送过的新机会，避免雷达天天重复。

- seen.json: {url: 最后推送日期}，本地文件、agent 私人记忆（同 chat_log，不是数据库）。
- filter_fresh: 新机会优先；不够 min_keep 时用旧的回退补满，保证日报不空。
- mark_seen: 推送成功后才登记，失败不抑制次日。
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

SEEN = Path(__file__).resolve().parent.parent / "data" / "seen.json"
TTL_DAYS = 14  # 超过这天数没再出现，视作"又新"可重推


def _load() -> dict:
    if not SEEN.exists():
        return {}
    try:
        return json.loads(SEEN.read_text())
    except Exception:
        return {}


def _is_recent(iso: str) -> bool:
    try:
        return datetime.fromisoformat(iso).date() > date.today() - timedelta(days=TTL_DAYS)
    except Exception:
        return False


def filter_fresh(opps: list[dict], min_keep: int = 15) -> list[dict]:
    """opps 已按 signal 排序。返回：未推过的在前，必要时用近期推过的回退补到 min_keep。"""
    seen = _load()
    fresh, repeat = [], []
    for o in opps:
        url = o.get("url", "")
        (repeat if url and _is_recent(seen.get(url, "")) else fresh).append(o)
    if len(fresh) >= min_keep:
        return fresh
    return fresh + repeat[: max(0, min_keep - len(fresh))]


def mark_seen(opps: list[dict]) -> None:
    seen = _load()
    today = date.today().isoformat()
    for o in opps:
        if o.get("url"):
            seen[o["url"]] = today
    # 顺手清理过期项，文件不无限膨胀
    seen = {u: d for u, d in seen.items() if _is_recent(d)}
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(seen, ensure_ascii=False))
