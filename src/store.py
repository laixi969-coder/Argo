"""机会历史存储：每天一份快照，让 Web 能分页 / 按日期分组 / 出详情页。

文件存储，不进数据库：data/history/YYYY-MM-DD.json，每个机会带稳定 id。
load_all() 跨天合并、按日期倒序；get(id) 给详情页用。
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import date
from pathlib import Path

from src import kv

DATA = Path(__file__).resolve().parent.parent / "data"
HISTORY = DATA / "history"
LATEST = DATA / "latest_report.json"


def item_id(o: dict) -> str:
    return hashlib.md5((o.get("url", "") or o.get("idea", "")).encode()).hexdigest()[:10]


def append(opps: list[dict], day: str | None = None) -> None:
    """存当天快照（覆盖同日，便于重跑）。生产写 KV，本地写文件。"""
    day = day or date.today().isoformat()
    enriched = [dict(o, id=item_id(o), date=day) for o in opps]
    if kv.enabled():
        kv.set_json(f"history:{day}", enriched)
        kv.sadd("history:days", day)
        return
    HISTORY.mkdir(parents=True, exist_ok=True)
    # 原子写：web 在并发读历史，避免读到半截文件
    p = HISTORY / f"{day}.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(enriched, ensure_ascii=False))
    os.replace(tmp, p)


def load_days() -> list[tuple[str, list[dict]]]:
    """返回 [(日期, 机会列表), ...]，日期倒序。无历史时回退当天 latest_report。"""
    if kv.enabled():
        days = sorted(kv.smembers("history:days"), reverse=True)
        out = []
        for d in days:
            opps = kv.get_json(f"history:{d}")
            if opps:
                out.append((d, opps))
        return out
    if HISTORY.exists():
        days = sorted((p for p in HISTORY.glob("*.json")), reverse=True)
        if days:
            out = []
            for p in days:
                try:
                    out.append((p.stem, json.loads(p.read_text())))
                except Exception:
                    continue
            return out
    if LATEST.exists():
        try:
            opps = json.loads(LATEST.read_text())
            today = date.today().isoformat()
            return [(today, [dict(o, id=item_id(o), date=today) for o in opps])]
        except Exception:
            return []
    return []


def load_flat() -> list[dict]:
    """所有机会拉平成一个列表（已带 id/date），按日期倒序、组内保持榜单顺序。"""
    return [o for _, opps in load_days() for o in opps]


def get(item_id_: str) -> dict | None:
    for o in load_flat():
        if o.get("id") == item_id_:
            return o
    return None
