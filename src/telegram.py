"""Telegram 收发底座：标准库直连，不引第三方库。

- send_message: 发一条消息给蔡蔡（Markdown）。
- get_updates: 长轮询拉新消息，offset 用于确认已读。
"""
from __future__ import annotations
import html
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from src import config

_API = "https://api.telegram.org/bot{token}/{method}"
_RETRIES = 2  # 清晨网络抖动重试，避免每日推送丢一天


def esc(text: str) -> str:
    """转义 HTML 特殊字符，防止 LLM 文本里的 < & 把消息打 400。"""
    return html.escape(str(text), quote=False)


def attr(text: str) -> str:
    """属性安全转义：连双/单引号一并转义，用于 href/src/value 等 HTML 属性，防属性逃逸注入。"""
    return html.escape(str(text), quote=True)


def safe_url(value: str) -> str:
    """只允许可点击的 HTTP(S) 外链，拒绝 javascript/data 等危险协议。"""
    value = str(value or "").strip()
    parts = urllib.parse.urlsplit(value)
    return value if parts.scheme in {"http", "https"} and parts.netloc else "#"


def _call(method: str, params: dict, timeout: int = 35) -> dict:
    token = config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 未配置")
    url = _API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode("utf-8")
    last = None
    for attempt in range(_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read())
            if not body.get("ok"):
                raise RuntimeError(f"Telegram {method} 失败: {body}")
            return body["result"]
        except urllib.error.HTTPError as e:
            # 4xx 是请求本身的错（如消息格式非法），重试无意义，直接抛
            if 400 <= e.code < 500:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e  # 连接/超时类，可重试
        if attempt < _RETRIES:
            time.sleep(1.5 * (attempt + 1))
    raise last


def send_message(text: str, chat_id: str | None = None, parse_mode: str | None = "HTML") -> None:
    """parse_mode=HTML 用于推送（telegram_report 已转义动态字段）；
    bot 回复传 parse_mode=None 按纯文本发，免去转义、绝不 400。"""
    send_to = chat_id or config.get("TELEGRAM_CHAT_ID")
    if not send_to:
        raise RuntimeError("TELEGRAM_CHAT_ID 未配置")
    # Telegram 单条上限 4096 字符，超了就切段发
    for chunk in _split(text, 4000):
        params = {
            "chat_id": send_to,
            "text": chunk,
            "disable_web_page_preview": "true",
        }
        if parse_mode:
            params["parse_mode"] = parse_mode
        _call("sendMessage", params)


def get_me() -> dict:
    """探活：返回机器人自身信息，验证 token 有效。"""
    return _call("getMe", {}, timeout=15)


def get_updates(offset: int | None = None, timeout: int = 30) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    return _call("getUpdates", params, timeout=timeout + 5)


def _split(text: str, n: int) -> list[str]:
    return [text[i:i + n] for i in range(0, len(text), n)] or [""]
