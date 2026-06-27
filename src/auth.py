"""认证：无状态 HMAC 签名会话 cookie。

cookie = "<uid>.<sig>"，sig = HMAC-SHA256(secret, uid)。验签通过即登录态。
secret 取 config.ARGO_SECRET，缺失则生成并持久化到 data/.secret（仅本机可读）。
"""
from __future__ import annotations
import hmac
import hashlib
import os
from http.cookies import SimpleCookie
from pathlib import Path
from src import config, users

COOKIE = "argo_session"
_SECRET_FILE = Path(__file__).resolve().parent.parent / "data" / ".secret"
THROTTLE = Path(__file__).resolve().parent.parent / "data" / "throttle"
_MAX_FAILS = 5
_WINDOW = 900  # 锁定 15 分钟


def _tpath(email: str) -> Path:
    return THROTTLE / (hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16] + ".json")


def login_blocked(email: str) -> bool:
    import json
    import time
    p = _tpath(email)
    if not p.exists():
        return False
    try:
        d = json.loads(p.read_text())
        return d.get("fails", 0) >= _MAX_FAILS and time.time() < d.get("until", 0)
    except Exception:
        return False


def note_fail(email: str) -> None:
    import json
    import time
    p = _tpath(email)
    fails = 0
    if p.exists():
        try:
            fails = json.loads(p.read_text()).get("fails", 0)
        except Exception:
            fails = 0
    fails += 1
    THROTTLE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"fails": fails, "until": int(time.time()) + _WINDOW}))


def note_ok(email: str) -> None:
    p = _tpath(email)
    if p.exists():
        p.unlink()


def _secret() -> bytes:
    s = config.get("ARGO_SECRET")
    if s:
        return s.encode()
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_bytes()
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    val = os.urandom(32)
    _SECRET_FILE.write_bytes(val)
    os.chmod(_SECRET_FILE, 0o600)
    return val


def _sign(uid: str) -> str:
    return hmac.new(_secret(), uid.encode(), hashlib.sha256).hexdigest()[:32]


def make_reset_token(uid: str, ttl: int = 3600) -> str:
    import time
    exp = int(time.time()) + ttl
    sig = hmac.new(_secret(), f"{uid}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{uid}.{exp}.{sig}"


def verify_reset_token(token: str):
    import time
    try:
        uid, exp, sig = token.split(".")
        good = hmac.new(_secret(), f"{uid}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good) or int(exp) < time.time():
            return None
        return uid
    except Exception:
        return None


def make_cookie(uid: str, secure: bool = False) -> str:
    """生成 Set-Cookie 头值。"""
    token = f"{uid}.{_sign(uid)}"
    parts = [f"{COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Lax", "Max-Age=2592000"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def clear_cookie() -> str:
    return f"{COOKIE}=; Path=/; HttpOnly; Max-Age=0"


def current_user(cookie_header: str) -> dict | None:
    """从请求 Cookie 头解析当前用户，验签失败返回 None。"""
    if not cookie_header:
        return None
    try:
        jar = SimpleCookie()
        jar.load(cookie_header)
        if COOKIE not in jar:
            return None
        token = jar[COOKIE].value
        uid, _, sig = token.partition(".")
        if not uid or not hmac.compare_digest(sig, _sign(uid)):
            return None
        u = users.get(uid)
        return {"id": uid, "email": u["email"], "plan": u.get("plan", "free")} if u else None
    except Exception:
        return None
