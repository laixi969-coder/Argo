"""Vercel WSGI 入口 — 把 stdlib route() 包成 WSGI app。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 让 src 包可导入
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import web, auth, admin  # noqa: E402

STATIC = ROOT / "static"
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
         ".ico": "image/x-icon", ".css": "text/css", ".js": "application/javascript"}


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    qs = environ.get("QUERY_STRING", "")
    raw_path = f"{path}?{qs}" if qs else path

    # ── 静态资源 ──
    if method == "GET" and path.startswith("/static/"):
        return _static(path[len("/static/"):], start_response)

    # ── 读 body ──
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (ValueError, TypeError):
        length = 0
    body = environ["wsgi.input"].read(length) if length else b""

    # ── 组装 headers dict（和 _Handler 保持一致）──
    headers = {}
    for key, val in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").lower()
            headers[name] = val
    if "CONTENT_TYPE" in environ:
        headers["content-type"] = environ["CONTENT_TYPE"]

    # ── 舰长设置 ──
    bare = path.split("?")[0]
    if bare == "/settings" or bare.startswith("/settings/"):
        inner = raw_path[len("/settings"):] or "/"
        status, ctype, text, extra = admin.handle_request(method, inner, body, headers)
        resp_headers = [("Content-Type", f"{ctype}; charset=utf-8"),
                        ("Cache-Control", "no-store"),
                        ("X-Content-Type-Options", "nosniff"),
                        ("X-Frame-Options", "DENY"),
                        ("Referrer-Policy", "strict-origin-when-cross-origin")]
        for k, v in extra.items():
            resp_headers.append((k, v))
        payload = text.encode("utf-8")
        resp_headers.append(("Content-Length", str(len(payload))))
        start_response(_status_line(status), resp_headers)
        return [payload]

    # ── 认证流（signup / login / logout 等，需要 Set-Cookie）──
    act = web.auth_action(method, raw_path, body, headers)
    if act is not None:
        status, extra, text = act
        payload = text.encode("utf-8")
        resp_headers = [("Content-Type", "text/html; charset=utf-8"),
                        ("Content-Length", str(len(payload))),
                        ("X-Content-Type-Options", "nosniff"),
                        ("X-Frame-Options", "DENY"),
                        ("Referrer-Policy", "strict-origin-when-cross-origin")]
        for k, v in extra:
            resp_headers.append((k, v))
        start_response(_status_line(status), resp_headers)
        return [payload]

    # ── 正常路由 ──
    status, ctype, text = web.route(method, raw_path, body, headers)
    payload = text.encode("utf-8")
    resp_headers = [("Content-Type", ctype),
                    ("Content-Length", str(len(payload))),
                    ("X-Content-Type-Options", "nosniff"),
                    ("X-Frame-Options", "DENY"),
                    ("Referrer-Policy", "strict-origin-when-cross-origin")]
    start_response(_status_line(status), resp_headers)
    return [payload]


def _static(name, start_response):
    safe = Path(name).name
    f = STATIC / safe
    if not f.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"not found"]
    suffix = f.suffix.lower()
    ctype = _MIME.get(suffix, "application/octet-stream")
    data = f.read_bytes()
    start_response("200 OK", [
        ("Content-Type", ctype),
        ("Content-Length", str(len(data))),
        ("Cache-Control", "public, max-age=86400"),
    ])
    return [data]


def _status_line(code: int) -> str:
    phrases = {200: "OK", 303: "See Other", 400: "Bad Request",
               401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
               503: "Service Unavailable"}
    return f"{code} {phrases.get(code, 'Unknown')}"
