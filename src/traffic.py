"""请求体限制和分布式限流，保护公开站点免受抓取与成本型滥用。"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass

from src import kv

MAX_BODY_BYTES = 32 * 1024
MAX_PATH_BYTES = 4 * 1024


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0
    status: int = 429
    reason: str = "请求过于频繁，请稍后再试"


_memory_lock = threading.Lock()
_memory_windows: dict[str, tuple[float, int]] = {}


def size_decision(*, raw_path: str, content_length: int) -> Decision | None:
    if len(raw_path.encode("utf-8", "ignore")) > MAX_PATH_BYTES:
        return Decision(False, status=414, reason="请求地址过长")
    if content_length < 0:
        return Decision(False, status=400, reason="无效的 Content-Length")
    if content_length > MAX_BODY_BYTES:
        return Decision(False, status=413, reason="请求体过大")
    return None


def check(method: str, raw_path: str, client_ip: str) -> Decision:
    """按风险分档限流。IP 仅做哈希后作为 KV key 的一部分，不写入业务数据。"""
    path = raw_path.split("?", 1)[0]
    name, limit, window, costly = _policy(method, path)
    if not name:
        return Decision(True)
    identity = hashlib.sha256((client_ip or "unknown").encode("utf-8")).hexdigest()[:24]
    key = f"{name}:{identity}"
    try:
        allowed, retry_after = kv.fixed_window(key, limit=limit, window=window)
        return Decision(allowed, retry_after=max(1, retry_after) if not allowed else 0)
    except RuntimeError:
        # Vercel 上昂贵的 LLM 接口宁可暂时拒绝，也不能在限流存储故障时裸奔。
        if costly and os.environ.get("VERCEL"):
            return Decision(False, status=503, reason="保护服务暂时不可用，请稍后重试")
        return _memory_check(key, limit=limit, window=window)


def _policy(method: str, path: str) -> tuple[str, int, int, bool]:
    if method == "POST" and path == "/api/chat":
        return "chat", 12, 60, True
    if method == "POST" and path in ("/signup", "/login", "/forgot", "/reset"):
        return "auth", 12, 600, False
    if path.startswith("/settings"):
        return "settings", 30, 60, False
    if method == "POST":
        return "write", 30, 60, False
    if path.startswith("/api/"):
        return "api-read", 120, 60, False
    if method == "GET":
        return "read", 240, 60, False
    return "other", 60, 60, False


def _memory_check(key: str, *, limit: int, window: int) -> Decision:
    """本机和 KV 短暂故障时的进程内降级，不将原始地址写盘。"""
    now = time.monotonic()
    with _memory_lock:
        reset_at, count = _memory_windows.get(key, (now + window, 0))
        if now >= reset_at:
            reset_at, count = now + window, 0
        count += 1
        _memory_windows[key] = (reset_at, count)
    if count > limit:
        return Decision(False, retry_after=max(1, int(reset_at - now)))
    return Decision(True)


def _reset_for_tests() -> None:
    with _memory_lock:
        _memory_windows.clear()
