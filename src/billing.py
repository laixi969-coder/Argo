"""计费：Stripe 接口位。

现在不接真实支付（需 Stripe 密钥 + 上线，属红线，留给蔡蔡）。
当前只登记「升级意向」到 data/billing_intents.jsonl，供验证付费意愿。
接 Stripe 时在 create_checkout 里实现，路由位已留好。
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from src import config

INTENTS = Path(__file__).resolve().parent.parent / "data" / "billing_intents.jsonl"


def record_intent(uid: str, email: str, plan: str = "pro") -> None:
    INTENTS.parent.mkdir(parents=True, exist_ok=True)
    with INTENTS.open("a") as f:
        f.write(json.dumps({"t": int(time.time()), "uid": uid, "email": email,
                            "plan": plan}, ensure_ascii=False) + "\n")


def intents() -> list[dict]:
    """全部升级意向（运营看付费意愿）。"""
    if not INTENTS.exists():
        return []
    out = []
    for line in INTENTS.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def stripe_ready() -> bool:
    return bool(config.get("STRIPE_SECRET_KEY"))


def create_checkout(uid: str, plan: str = "pro") -> str:
    """接 Stripe 后返回支付链接。未配置密钥时抛错（调用方需先 stripe_ready 判断）。"""
    if not stripe_ready():
        raise RuntimeError("STRIPE_SECRET_KEY 未配置，支付未接入")
    # ponytail: Stripe Checkout Session 在此创建，返回 session.url
    raise NotImplementedError("Stripe 接入待实现")
