"""机会历史存储：每天一份快照，让 Web 能分页 / 按日期分组 / 出详情页。

文件存储，不进数据库：data/history/YYYY-MM-DD.json，每个机会带稳定 id。
load_all() 跨天合并、按日期倒序；get(id) 给详情页用。
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from src import clock, kv

DATA = Path(__file__).resolve().parent.parent / "data"
HISTORY = DATA / "history"
LATEST = DATA / "latest_report.json"


def item_id(o: dict) -> str:
    return hashlib.md5((o.get("url", "") or o.get("idea", "")).encode()).hexdigest()[:10]


def is_demo_item(o: dict) -> bool:
    """识别离线演示夹具，生产读取与合并时一律隔离。"""
    url = o.get("url", "")
    return bool(o.get("_demo")) or url in {f"https://example.com/{i}" for i in range(6)}


def _merge(existing: list[dict] | None, incoming: list[dict], day: str) -> list[dict]:
    """合并同日多班扫描；同一机会用新结果刷新，历史机会不丢。"""
    merged = {}
    for o in [*(existing or []), *incoming]:
        if is_demo_item(o):
            continue
        enriched = dict(o)
        enriched["id"] = item_id(enriched)
        enriched["date"] = day
        merged[enriched["id"]] = enriched
    return sorted(merged.values(), key=lambda o: o.get("score", 0), reverse=True)


def append(opps: list[dict], day: str | None = None) -> None:
    """存当天快照；空结果不覆盖同日已有榜单。生产写 KV，本地写文件。"""
    day = day or clock.today_iso()
    enriched = [dict(o, id=item_id(o), date=day) for o in opps]
    if kv.enabled():
        existing = kv.get_json(f"history:{day}")
        if not enriched and existing:
            print(f"[warn] 今日重跑产出 0 条，保留已有 {len(existing)} 条机会")
            return
        kv.set_json(f"history:{day}", _merge(existing, enriched, day))
        kv.sadd("history:days", day)
        return
    HISTORY.mkdir(parents=True, exist_ok=True)
    # 原子写：web 在并发读历史，避免读到半截文件
    p = HISTORY / f"{day}.json"
    existing = []
    if p.exists():
        try:
            existing = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            existing = []
    if not enriched and existing:
        print(f"[warn] 今日重跑产出 0 条，保留已有 {len(existing)} 条机会")
        return
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_merge(existing, enriched, day), ensure_ascii=False))
    os.replace(tmp, p)


def load_days() -> list[tuple[str, list[dict]]]:
    """返回 [(日期, 机会列表), ...]，日期倒序。无历史时回退当天 latest_report。"""
    if kv.enabled():
        days = sorted(kv.smembers("history:days"), reverse=True)
        out = []
        for d in days:
            opps = kv.get_json(f"history:{d}")
            # 空榜也是一次有效的今日更新，不能因此回退显示昨天。
            if opps is not None:
                out.append((d, [o for o in opps if not is_demo_item(o)]))
        return out
    if HISTORY.exists():
        days = sorted((p for p in HISTORY.glob("*.json")), reverse=True)
        if days:
            out = []
            for p in days:
                try:
                    out.append((p.stem, [o for o in json.loads(p.read_text()) if not is_demo_item(o)]))
                except Exception:
                    continue
            return out
    if LATEST.exists():
        try:
            opps = json.loads(LATEST.read_text())
            today = clock.today_iso()
            return [(today, [dict(o, id=item_id(o), date=today) for o in opps])]
        except Exception:
            return []
    return []


def load_flat() -> list[dict]:
    """所有机会拉平成一个列表（已带 id/date），按日期倒序、组内保持榜单顺序。"""
    return [o for _, opps in load_days() for o in opps]


def load_day(day: str | None = None, *, include_demo: bool = False) -> list[dict] | None:
    """读取指定业务日；不存在返回 None，空榜返回 []。"""
    day = day or clock.today_iso()
    if kv.enabled():
        opps = kv.get_json(f"history:{day}")
        return opps if include_demo or opps is None else [o for o in opps if not is_demo_item(o)]
    p = HISTORY / f"{day}.json"
    if not p.exists():
        return None
    try:
        opps = json.loads(p.read_text())
        return opps if include_demo else [o for o in opps if not is_demo_item(o)]
    except (OSError, json.JSONDecodeError):
        return None


def get(item_id_: str) -> dict | None:
    # 绝大多数详情/深挖来自今日榜单，先用一次 KV 请求命中，避免扫描全部历史。
    for o in load_day() or []:
        if o.get("id") == item_id_:
            return o
    for o in load_flat():
        if o.get("id") == item_id_:
            return o
    return None
