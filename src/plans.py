"""历史会员字段兼容层。

当前所有注册用户均免费访问完整榜单与不限次深挖；这些定义仅用于兼容旧账号数据，
不再参与 Web/API 门控。
"""
from __future__ import annotations
import json
from pathlib import Path
from src import clock, kv

QUOTA_DIR = Path(__file__).resolve().parent.parent / "data" / "quota"

# 旧账号可能仍带 free/pro 字段；两者当前权益完全相同。
PLANS = {
    "free": {
        "name": "免费版", "price_cny": 0,
        "feed_limit": 999,
        "chat_per_day": 999,
        "history_days": 90,
        "blurb": "完整榜单 + 不限深挖",
    },
    "pro": {
        "name": "专业版", "price_cny": 0,
        "feed_limit": 999,
        "chat_per_day": 999,
        "history_days": 90,
        "blurb": "完整榜单 + 不限深挖",
    },
}
DEFAULT = "free"


def plan_of(user: dict | None) -> dict:
    key = (user or {}).get("plan", DEFAULT)
    return PLANS.get(key, PLANS[DEFAULT])


def feed_limit(user: dict | None) -> int:
    return plan_of(user)["feed_limit"]


def history_days(user: dict | None) -> int:
    return plan_of(user)["history_days"]


def _quota_path(uid: str) -> Path:
    return QUOTA_DIR / f"{uid}-{clock.today_iso().replace('-', '')}.json"


def chat_remaining(user: dict | None) -> int:
    if not user:
        return 0
    used = _used(user["id"])
    return max(0, plan_of(user)["chat_per_day"] - used)


def use_chat(user: dict | None) -> bool:
    """消耗一次深挖配额。够用返回 True 并计数，超限返回 False。"""
    if not user:
        return False
    if chat_remaining(user) <= 0:
        return False
    if kv.enabled():
        kv.set_json(_quota_key(user["id"]), {"chat": _used(user["id"]) + 1}, ex=172800)
        return True
    p = _quota_path(user["id"])
    QUOTA_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"chat": _used(user["id"]) + 1}))
    return True


def _used(uid: str) -> int:
    if kv.enabled():
        return int((kv.get_json(_quota_key(uid)) or {}).get("chat", 0))
    p = _quota_path(uid)
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text()).get("chat", 0))
    except Exception:
        return 0


def _quota_key(uid: str) -> str:
    return f"quota:{uid}:{clock.today_iso().replace('-', '')}"
