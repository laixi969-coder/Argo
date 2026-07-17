"""用户收藏：data/saved/<uid>.json = [item_id,...]。按用户隔离。"""
from __future__ import annotations
import json
import os
from pathlib import Path
from src import kv

SAVED = Path(__file__).resolve().parent.parent / "data" / "saved"


def _path(uid: str) -> Path:
    return SAVED / f"{uid}.json"


def list_ids(uid: str) -> list[str]:
    if kv.enabled():
        return kv.get_json(f"saved:{uid}") or []
    p = _path(uid)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def all_item_ids() -> set[str]:
    """返回仍被任意账户收藏的机会 ID，供历史到期清理保留这些内容。"""
    if kv.enabled():
        uids = kv.smembers("users")
        lists = kv.get_many_json([f"saved:{uid}" for uid in uids])
        return {
            item_id for ids in lists if isinstance(ids, list)
            for item_id in ids if isinstance(item_id, str)
        }
    if not SAVED.exists():
        return set()
    kept = set()
    for path in SAVED.glob("*.json"):
        try:
            ids = json.loads(path.read_text())
        except Exception:
            continue
        if isinstance(ids, list):
            kept.update(item_id for item_id in ids if isinstance(item_id, str))
    return kept


def purge(uid: str) -> None:
    if kv.enabled():
        kv.delete(f"saved:{uid}")
        return
    p = _path(uid)
    if p.exists():
        p.unlink()


def is_saved(uid: str, item_id: str) -> bool:
    return item_id in list_ids(uid)


def toggle(uid: str, item_id: str) -> bool:
    """收藏/取消，返回新状态（True=已收藏）。"""
    ids = list_ids(uid)
    saved = item_id not in ids
    if saved:
        ids.insert(0, item_id)
    else:
        ids.remove(item_id)
    if kv.enabled():
        kv.set_json(f"saved:{uid}", ids)
        return saved
    SAVED.mkdir(parents=True, exist_ok=True)
    p = _path(uid)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ids, ensure_ascii=False))
    os.replace(tmp, p)
    return saved
