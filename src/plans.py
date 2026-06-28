"""会员分层 + 功能门控 + 配额。

产品形态：每日机会流是共享内容；付费解锁「深挖对话」「完整榜单」「更多来源」。
计费：真实支付（Stripe）接口位留在 billing 里，这里只定义计划与权益。
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from src import kv

QUOTA_DIR = Path(__file__).resolve().parent.parent / "data" / "quota"

# 计划定义：权益 + 价格（分/月）。免费可看摘要，付费解锁深挖与完整内容。
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
    return QUOTA_DIR / f"{uid}-{time.strftime('%Y%m%d')}.json"


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
    return f"quota:{uid}:{time.strftime('%Y%m%d')}"
