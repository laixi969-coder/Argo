"""轻量持久化 KV：Vercel 用 Upstash REST，本机继续用文件。

不引入第三方 SDK，直接调用 Upstash Redis REST API。只有同时配置
UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN 时才启用。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional


def enabled() -> bool:
    return bool(_url() and _token())


def cloud_missing() -> list[str]:
    """Vercel 运行账号系统所缺的配置；本机永远返回空。"""
    if not os.environ.get("VERCEL"):
        return []
    missing = []
    if not _url():
        missing.append("KV_REST_API_URL")
    if not _token():
        missing.append("KV_REST_API_TOKEN")
    if not os.environ.get("ARGO_SECRET"):
        missing.append("ARGO_SECRET")
    return missing


def get_json(key: str):
    raw = command("GET", _key(key))
    return json.loads(raw) if raw is not None else None


def set_json(key: str, value, *, ex: Optional[int] = None, nx: bool = False) -> bool:
    args = ["SET", _key(key), json.dumps(value, ensure_ascii=False)]
    if nx:
        args.append("NX")
    if ex is not None:
        args.extend(("EX", int(ex)))
    return command(*args) == "OK"


def delete(key: str) -> None:
    command("DEL", _key(key))


def sadd(key: str, value: str) -> None:
    command("SADD", _key(key), value)


def srem(key: str, value: str) -> None:
    command("SREM", _key(key), value)


def smembers(key: str) -> list[str]:
    return command("SMEMBERS", _key(key)) or []


def append_json(key: str, value, *, max_items: int = 200, ex: int | None = None) -> None:
    """向 JSON 日志列表追加一条并限制长度；供 serverless 对话日志使用。"""
    script = (
        "redis.call('rpush', KEYS[1], ARGV[1]); "
        "redis.call('ltrim', KEYS[1], -tonumber(ARGV[2]), -1); "
        "if tonumber(ARGV[3]) > 0 then redis.call('expire', KEYS[1], ARGV[3]); end; "
        "return 1"
    )
    command("EVAL", script, 1, _key(key), json.dumps(value, ensure_ascii=False),
            int(max_items), int(ex or 0))


def list_json(key: str, start: int = 0, end: int = -1) -> list:
    out = []
    for raw in command("LRANGE", _key(key), start, end) or []:
        try:
            out.append(json.loads(raw))
        except (TypeError, json.JSONDecodeError):
            continue
    return out


def acquire_lock(name: str, owner: str, ttl: int = 3600) -> bool:
    """跨进程互斥锁；防 GitHub / 本机 / 手动任务同时覆盖历史。"""
    return set_json(f"lock:{name}", owner, ex=ttl, nx=True)


def release_lock(name: str, owner: str) -> bool:
    """只释放自己持有的锁，避免旧任务误删新任务的锁。"""
    script = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) else return 0 end"
    )
    encoded_owner = json.dumps(owner, ensure_ascii=False)
    return bool(command("EVAL", script, 1, _key(f"lock:{name}"), encoded_owner))


def command(*args):
    if not enabled():
        raise RuntimeError("Upstash Redis 未配置")
    url = _url().rstrip("/")
    token = _token()
    req = urllib.request.Request(
        url,
        data=json.dumps(list(args), ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("持久化存储暂时不可用") from exc
    if payload.get("error"):
        raise RuntimeError(f"持久化存储错误：{payload['error']}")
    return payload.get("result")


def _key(key: str) -> str:
    prefix = os.environ.get("ARGO_KV_PREFIX", "argo")
    return f"{prefix}:{key}"


def _url() -> str:
    return (os.environ.get("UPSTASH_REDIS_REST_URL") or
            os.environ.get("KV_REST_API_URL") or "")


def _token() -> str:
    return (os.environ.get("UPSTASH_REDIS_REST_TOKEN") or
            os.environ.get("KV_REST_API_TOKEN") or "")
