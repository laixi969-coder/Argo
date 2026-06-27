import smtplib
from email.mime.text import MIMEText
from html import escape
from urllib.parse import urlsplit

from src import config


def _safe_url(value):
    value = str(value or "")
    return value if urlsplit(value).scheme in {"http", "https"} else "#"


def render_html(opps, missing_sources):
    rows = "".join(
        f"<tr><td>{i + 1}</td><td>{escape(str(o.get('idea', '')))}</td>"
        f"<td>{escape(str(o.get('verdict', '待验证')))}</td>"
        f"<td>{int(o.get('score', 0))}</td>"
        f"<td>{escape(str(o.get('demand_evidence', '未提取到证据')))}</td>"
        f"<td>{escape(str(o.get('reason', '')))}</td>"
        f"<td>{escape(str(o.get('next_validation', '补采真实支付证据')))}</td>"
        f"<td><a href='{escape(_safe_url(o.get('url')), quote=True)}'>"
        f"{escape(str(o.get('source', '来源')))}</a></td></tr>"
        for i, o in enumerate(opps)
    )
    notice = (
        f"<p style='color:#c00'>今天这些源没抓到：{escape(', '.join(missing_sources))}</p>"
        if missing_sources
        else ""
    )
    body = (
        "<p>今日无机会入榜。</p>"
        if not opps
        else (
            "<table border=1 cellpadding=6 style='border-collapse:collapse'>"
            "<tr><th>#</th><th>产品机会</th><th>判定</th><th>分</th>"
            "<th>原始证据</th><th>判断理由</th><th>下一步验证</th><th>来源</th></tr>"
            f"{rows}</table>"
        )
    )
    return f"<h2>金羊毛 Argo · 今日选品 Top {len(opps)}</h2>{notice}{body}"


def send_report(opps, missing_sources):
    msg = MIMEText(render_html(opps, missing_sources), "html", "utf-8")
    msg["Subject"] = f"金羊毛 Argo · 今日 {len(opps)} 个机会"
    msg["From"] = config.get("SMTP_USER")
    msg["To"] = config.get("REPORT_TO")
    with smtplib.SMTP(config.get("SMTP_HOST"), int(config.get("SMTP_PORT"))) as s:
        s.starttls()
        s.login(config.get("SMTP_USER"), config.get("SMTP_PASS"))
        s.send_message(msg)
