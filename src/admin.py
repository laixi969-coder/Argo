"""Argo 本机超级管理员设置页。仅监听 localhost。"""

import json
import secrets
import smtplib
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests

from src.settings import (
    ENV_PATH,
    _read_values,
    _replace_value,
    verify_password,
)


HOST = "127.0.0.1"
PORT = 8765
SESSION_TTL = 8 * 60 * 60
PAGE_PATH = Path(__file__).with_name("admin.html")
SESSIONS = {}

PUBLIC_FIELDS = (
    "LLM_BASE_URL",
    "LLM_MODEL",
    "REDDIT_CLIENT_ID",
    "TIKHUB_BASE_URL",
    "REDFOX_BASE_URL",
    "REDFOX_TEST_PATH",
    "REDFOX_AUTH_HEADER",
    "REDFOX_AUTH_PREFIX",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "REPORT_TO",
)
SECRET_FIELDS = (
    "LLM_API_KEY",
    "REDDIT_CLIENT_SECRET",
    "PRODUCTHUNT_TOKEN",
    "TIKHUB_API_KEY",
    "REDFOX_API_KEY",
    "SMTP_PASS",
)
ALL_FIELDS = PUBLIC_FIELDS + SECRET_FIELDS


def _configured(value):
    return bool(str(value or "").strip())


def safe_settings(values):
    result = {key: values.get(key, "") for key in PUBLIC_FIELDS}
    result["configured"] = {
        key: _configured(values.get(key)) for key in ALL_FIELDS
    }
    return result


def merged_settings(payload, path=ENV_PATH):
    values = _read_values(path)
    for key in PUBLIC_FIELDS:
        if key in payload:
            values[key] = str(payload[key]).strip()
    for key in SECRET_FIELDS:
        value = str(payload.get(key, "")).strip()
        if value:
            values[key] = value
    return values


def save_settings(payload, path=ENV_PATH):
    for key in ALL_FIELDS:
        value = str(payload.get(key, ""))
        if "\n" in value or "\r" in value:
            raise ValueError(f"{key} 不能包含换行")
    for key in PUBLIC_FIELDS:
        if key in payload:
            _replace_value(key, str(payload[key]).strip(), path)
    for key in SECRET_FIELDS:
        value = str(payload.get(key, "")).strip()
        if value:
            _replace_value(key, value, path)


def fetch_models(values, get=requests.get):
    base_url = values.get("LLM_BASE_URL", "").rstrip("/")
    api_key = values.get("LLM_API_KEY", "")
    if not base_url or not api_key:
        raise ValueError("请先填写 Base URL 和 API Key")
    response = get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    models = sorted(
        {str(item.get("id", "")).strip() for item in data if item.get("id")}
    )
    if not models:
        raise ValueError("接口返回成功，但没有找到模型")
    return models


def test_llm(values, post=requests.post):
    base_url = values.get("LLM_BASE_URL", "").rstrip("/")
    api_key = values.get("LLM_API_KEY", "")
    model = values.get("LLM_MODEL", "")
    if not base_url or not api_key or not model:
        raise ValueError("Base URL、API Key 和模型均不能为空")
    response = post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "只回复 OK"}],
            "temperature": 0,
            "max_tokens": 8,
        },
        timeout=30,
    )
    response.raise_for_status()
    response.json()["choices"][0]["message"]["content"]
    return f"LLM 连接成功，模型 {model} 可用"


def test_reddit(values, post=requests.post):
    client_id = values.get("REDDIT_CLIENT_ID", "")
    secret = values.get("REDDIT_CLIENT_SECRET", "")
    if not client_id or not secret:
        raise ValueError("Reddit Client ID 和 Secret 均不能为空")
    response = post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": "argo/0.1"},
        timeout=20,
    )
    response.raise_for_status()
    if not response.json().get("access_token"):
        raise ValueError("Reddit 未返回 access token")
    return "Reddit 连接成功"


def test_producthunt(values, post=requests.post):
    token = values.get("PRODUCTHUNT_TOKEN", "")
    if not token:
        raise ValueError("Product Hunt Token 不能为空")
    response = post(
        "https://api.producthunt.com/v2/api/graphql",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"query": "{ posts(first: 1) { edges { node { name } } } }"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise ValueError(payload["errors"][0].get("message", "Product Hunt 返回错误"))
    return "Product Hunt 连接成功"


def test_data_provider(values, prefix, label, get=requests.get):
    base_url = values.get(f"{prefix}_BASE_URL", "").rstrip("/")
    api_key = values.get(f"{prefix}_API_KEY", "")
    test_path = values.get(f"{prefix}_TEST_PATH", "").strip()
    header_name = values.get(f"{prefix}_AUTH_HEADER", "Authorization").strip()
    auth_prefix = values.get(f"{prefix}_AUTH_PREFIX", "Bearer").strip()
    if not base_url or not api_key or not test_path:
        raise ValueError(f"{label} 的 Base URL、API Key 和测试端点均不能为空")
    if not header_name or any(char in header_name for char in "\r\n:"):
        raise ValueError("鉴权 Header 名称无效")
    if test_path.startswith(("http://", "https://")):
        url = test_path
    else:
        url = f"{base_url}/{test_path.lstrip('/')}"
    credential = f"{auth_prefix} {api_key}".strip()
    response = get(url, headers={header_name: credential}, timeout=30)
    response.raise_for_status()
    return f"{label} 连接成功（HTTP {response.status_code}）"


def test_tikhub(values, get=requests.get):
    base_url = values.get("TIKHUB_BASE_URL", "").rstrip("/")
    api_key = values.get("TIKHUB_API_KEY", "")
    if not base_url or not api_key:
        raise ValueError("TikHub Base URL 和 API Key 均不能为空")
    response = get(
        f"{base_url}/api/v1/tikhub/user/get_user_info",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 200:
        raise ValueError(payload.get("message_zh") or payload.get("message") or "TikHub 返回异常")
    key_data = payload.get("api_key_data") or {}
    user_data = payload.get("user_data") or {}
    if key_data.get("api_key_status") != 1:
        raise ValueError("TikHub API Key 当前未启用")
    if user_data.get("account_disabled") or not user_data.get("is_active"):
        raise ValueError("TikHub 账户当前不可用")
    balance = user_data.get("balance", "未知")
    free_credit = user_data.get("free_credit", "未知")
    return f"TikHub 连接成功 · Key 正常 · 余额 {balance} · 免费额度 {free_credit}"


def test_redfox(values):
    return test_data_provider(values, "REDFOX", "红狐数据")


def test_smtp(values, smtp_factory=smtplib.SMTP):
    required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS")
    if any(not values.get(key) for key in required):
        raise ValueError("SMTP 地址、端口、用户和应用密码均不能为空")
    with smtp_factory(values["SMTP_HOST"], int(values["SMTP_PORT"]), timeout=20) as smtp:
        smtp.starttls()
        smtp.login(values["SMTP_USER"], values["SMTP_PASS"])
    return "SMTP 登录成功（未发送邮件）"


TESTERS = {
    "llm": test_llm,
    "reddit": test_reddit,
    "producthunt": test_producthunt,
    "tikhub": test_tikhub,
    "redfox": test_redfox,
    "smtp": test_smtp,
}


def _parse_body(raw_bytes, content_type=""):
    """解析请求 body：JSON 或 form。"""
    raw = raw_bytes.decode("utf-8") if isinstance(raw_bytes, bytes) else raw_bytes
    if "application/json" in content_type:
        return json.loads(raw or "{}")
    return {key: values[-1] for key, values in parse_qs(raw).items()}


def _get_session(headers):
    """从请求头取 admin session。"""
    cookie = SimpleCookie(headers.get("Cookie", "") if isinstance(headers, dict) else headers.get("cookie", ""))
    token = cookie.get("argo_session")
    if not token:
        return None
    session = SESSIONS.get(token.value)
    if not session or session["expires"] < time.time():
        SESSIONS.pop(token.value, None)
        return None
    return session


def _json_resp(payload, status=200, headers=None):
    return (status, "application/json", json.dumps(payload, ensure_ascii=False), headers or {})


def _page_resp():
    body = PAGE_PATH.read_text("utf-8")
    return (200, "text/html", body, {})


def handle_request(method, path, body=b"", headers=None):
    """纯函数路由：返回 (status, content_type, body_text, extra_headers_dict)。

    可被 web.py 调用，也可被 AdminHandler 调用。
    path 不含 /settings 前缀（调用方负责剥离）。
    """
    headers = headers or {}
    path = urlsplit(path).path

    if method == "GET":
        if path == "/":
            return _page_resp()
        if path == "/api/session":
            session = _get_session(headers)
            return _json_resp({"authenticated": bool(session), "csrf": session["csrf"] if session else ""})
        if path == "/api/settings":
            session = _get_session(headers)
            if not session:
                return _json_resp({"ok": False, "error": "请先登录"}, 401)
            return _json_resp({"ok": True, "settings": safe_settings(_read_values())})
        return _json_resp({"error": "not found"}, 404)

    if method == "POST":
        try:
            payload = _parse_body(body, headers.get("Content-Type", "") or headers.get("content-type", ""))
        except (ValueError, json.JSONDecodeError) as exc:
            return _json_resp({"ok": False, "error": str(exc)}, 400)

        if path == "/api/login":
            values = _read_values()
            email_ok = secrets.compare_digest(str(payload.get("email", "")).strip().lower(), values.get("ADMIN_EMAIL", "").strip().lower())
            password_ok = verify_password(str(payload.get("password", "")), values.get("ADMIN_PASSWORD_HASH", ""))
            if not email_ok or not password_ok:
                time.sleep(0.5)
                return _json_resp({"ok": False, "error": "邮箱或密码错误"}, 401)
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
            SESSIONS[token] = {"csrf": csrf, "expires": time.time() + SESSION_TTL}
            return _json_resp(
                {"ok": True, "csrf": csrf},
                headers={"Set-Cookie": f"argo_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}"},
            )

        session = _get_session(headers)
        if not session:
            return _json_resp({"ok": False, "error": "请先登录"}, 401)
        csrf_token = headers.get("X-CSRF-Token", "") or headers.get("x-csrf-token", "")
        if not secrets.compare_digest(csrf_token, session["csrf"]):
            return _json_resp({"ok": False, "error": "安全令牌失效，请刷新页面"}, 403)

        if path == "/api/settings":
            try:
                save_settings(payload)
                return _json_resp({"ok": True, "message": "设置已安全保存"})
            except ValueError as exc:
                return _json_resp({"ok": False, "error": str(exc)}, 400)
        if path == "/api/models":
            try:
                models = fetch_models(merged_settings(payload))
                return _json_resp({"ok": True, "models": models})
            except Exception as exc:
                return _json_resp({"ok": False, "error": str(exc)}, 502)
        if path == "/api/test":
            service = str(payload.get("service", ""))
            tester = TESTERS.get(service)
            if not tester:
                return _json_resp({"ok": False, "error": "未知服务"}, 400)
            try:
                message = tester(merged_settings(payload))
                return _json_resp({"ok": True, "message": message})
            except Exception as exc:
                return _json_resp({"ok": False, "error": str(exc)}, 502)
        return _json_resp({"error": "not found"}, 404)

    return _json_resp({"error": "method not allowed"}, 405)


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "ArgoAdmin/1.0"

    def log_message(self, fmt, *args):
        print(f"[admin] {self.address_string()} {fmt % args}")

    def _dispatch(self, method):
        path = self.path
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64_000:
            self.send_response(413)
            self.end_headers()
            return
        body = self.rfile.read(length) if length else b""
        hdrs = {k: v for k, v in self.headers.items()}
        status, ctype, text, extra = handle_request(method, path, body, hdrs)
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if ctype == "text/html":
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
            self.send_header("X-Frame-Options", "DENY")
        for k, v in extra.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def run(host=HOST, port=PORT):
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("管理员页面只允许监听本机地址")
    server = ThreadingHTTPServer((host, port), AdminHandler)
    print(f"Argo 超级管理员设置：http://{host}:{port}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
