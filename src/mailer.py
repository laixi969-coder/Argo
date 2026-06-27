"""轻量发信：复用项目已有的 SMTP_* 配置（标准库 smtplib）。

仅用于密码重置等事务邮件。SMTP 未配置时 configured() 返回 False，调用方据此降级。
"""
from __future__ import annotations
import smtplib
from email.mime.text import MIMEText
from src import config


def configured() -> bool:
    return bool(config.get("SMTP_USER") and config.get("SMTP_PASS"))


def send(to: str, subject: str, body: str) -> None:
    if not configured():
        raise RuntimeError("SMTP 未配置")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.get("SMTP_USER")
    msg["To"] = to
    with smtplib.SMTP(config.get("SMTP_HOST", "smtp.gmail.com"),
                      int(config.get("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(config.get("SMTP_USER"), config.get("SMTP_PASS"))
        s.send_message(msg)
