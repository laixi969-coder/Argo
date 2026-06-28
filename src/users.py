"""用户存储：文件型，不进数据库。data/users/<id>.json。

商业化地基。密码用 PBKDF2-HMAC-SHA256 加盐哈希，绝不明文。
多租户：每个用户独立 id，个人数据（收藏/对话/配额）按 id 隔离。
"""
from __future__ import annotations
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from src import kv

USERS = Path(__file__).resolve().parent.parent / "data" / "users"
_ITER = 200_000


def _uid(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16]


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITER).hex()


def _path(uid: str) -> Path:
    return USERS / f"{uid}.json"


def get(uid: str) -> dict | None:
    if kv.enabled():
        return kv.get_json(f"user:{uid}")
    p = _path(uid)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def get_by_email(email: str) -> dict | None:
    return get(_uid(email))


def create(email: str, password: str, plan: str = "free") -> dict:
    """创建用户。邮箱已存在或入参非法则抛 ValueError。"""
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 254:
        raise ValueError("邮箱格式不对")
    if not (8 <= len(password or "") <= 128):
        raise ValueError("密码需 8-128 位")
    uid = _uid(email)
    if get(uid):
        raise ValueError("该邮箱已注册")
    salt = secrets.token_hex(16)
    user = {"id": uid, "email": email, "salt": salt, "pw": _hash(password, salt),
            "plan": plan, "created": int(time.time())}
    if kv.enabled():
        if not kv.set_json(f"user:{uid}", user, nx=True):
            raise ValueError("该邮箱已注册")
        kv.sadd("users", uid)
    else:
        USERS.mkdir(parents=True, exist_ok=True)
        _write(uid, user)
    return _public(user)


def verify(email: str, password: str) -> dict | None:
    u = get_by_email(email)
    if not u:
        return None
    # 常量时间比较，防时序侧信道
    if secrets.compare_digest(_hash(password, u["salt"]), u["pw"]):
        return _public(u)
    return None


def set_password(uid: str, new_password: str) -> bool:
    if not (8 <= len(new_password or "") <= 128):
        raise ValueError("密码需 8-128 位")
    u = get(uid)
    if not u:
        return False
    u["salt"] = secrets.token_hex(16)
    u["pw"] = _hash(new_password, u["salt"])
    _write(uid, u)
    return True


def set_plan(uid: str, plan: str) -> dict | None:
    u = get(uid)
    if not u:
        return None
    u["plan"] = plan
    _write(uid, u)
    return _public(u)


def delete(uid: str) -> bool:
    if kv.enabled():
        existed = get(uid) is not None
        kv.delete(f"user:{uid}")
        kv.srem("users", uid)
        return existed
    p = _path(uid)
    if p.exists():
        p.unlink()
        return True
    return False


def count() -> int:
    if kv.enabled():
        return len(kv.smembers("users"))
    return len(list(USERS.glob("*.json"))) if USERS.exists() else 0


def all_users() -> list[dict]:
    """运营视角：全部用户（脱敏），按注册时间倒序。"""
    if kv.enabled():
        out = [get(uid) for uid in kv.smembers("users")]
        return sorted((_public(u) for u in out if u),
                      key=lambda u: u.get("created", 0), reverse=True)
    if not USERS.exists():
        return []
    out = []
    for p in USERS.glob("*.json"):
        try:
            out.append(_public(json.loads(p.read_text())))
        except Exception:
            continue
    return sorted(out, key=lambda u: u.get("created", 0), reverse=True)


def _public(u: dict) -> dict:
    """对外只暴露非敏感字段，绝不外泄 pw/salt。"""
    return {"id": u["id"], "email": u["email"], "plan": u.get("plan", "free"),
            "created": u.get("created", 0)}


def _write(uid: str, user: dict) -> None:
    if kv.enabled():
        kv.set_json(f"user:{uid}", user)
        kv.sadd("users", uid)
        return
    p = _path(uid)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(user, ensure_ascii=False))
    os.replace(tmp, p)
