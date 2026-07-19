"""渲染并推送每日榜单到 Telegram（HTML 模式，动态字段全转义）。

接口与原邮件模块一致：send_report(opps, missing)。
"""
from src import telegram
from src.visibility import visible_only

esc = telegram.esc

# 显示用的源名（合并细分变体到大名字），只影响展示，不动内部 source 值
_SOURCE_LABELS = {
    "reddit_tikhub": "Reddit",
    "reddit_comments_tikhub": "Reddit",
    "reddit": "Reddit",
    "producthunt": "Product Hunt",
    "hackernews": "Hacker News",
    "huggingface": "Hugging Face",
    "github": "GitHub",
    "futurepedia": "Futurepedia",
    "industry_cases": "AI 行业应用",
    "tikhub": "TikTok",
}


def _label(source: str) -> str:
    return _SOURCE_LABELS.get(source, source)


def _edge(o: dict) -> str:
    """交付范式标签：有值且非「未知」才显示，老数据无此字段不报错。"""
    edge = str(o.get("delivery_edge", "") or "").strip()
    return f" · 🎯{esc(edge)}" if edge and edge != "未知" else ""


def _labels(o: dict) -> str:
    parts = []
    potential = str(o.get("commercial_potential") or "").strip()
    if potential in {"高", "中", "低"}:
        parts.append(f"{potential}商业潜力")
    if o.get("industry") and o.get("industry") != "跨行业":
        parts.append(str(o["industry"]))
    parts.extend(f"#{tag}" for tag in (o.get("tags") or [])[:3])
    return " · ".join(esc(part) for part in parts)


def _item(o: dict, number: int) -> str:
    lines = [
        f"<b>{number}. {esc(o['idea'])}</b>",
        f"{esc(o['verdict'])} · {int(o['score'])}分 · "
        f"<a href=\"{telegram.attr(telegram.safe_url(o.get('url', '')))}\">"
        f"{esc(_label(o['source']))}</a>{_edge(o)}",
    ]
    labels = _labels(o)
    if labels:
        lines.append(labels)
    quotes = o.get("evidence_quotes") or []
    if quotes:
        lines.append(f"<blockquote>原文证据：{esc(quotes[0])}</blockquote>")
    elif o.get("radar_track") == "真实需求主榜":
        lines.append("<blockquote>原文证据：缺失（不应进入主榜）</blockquote>")
    lines.append(esc(o["reason"]))
    return "\n".join(lines)


def render(opps: list[dict], missing_sources: list[str]) -> str:
    opps = visible_only(opps)
    main = [o for o in opps if o.get("radar_track") == "真实需求主榜"]
    pending = [o for o in opps if o.get("radar_track") == "待核验证据副榜"]
    main.extend(o for o in opps if not o.get("radar_track"))
    supply = [o for o in opps if o.get("radar_track") == "AI 供给副榜"]
    head = f"<b>金羊毛 Argo · 今日选品 Top {len(opps)}</b>"
    if not opps:
        body = "今日无机会入榜。"
    else:
        sections = []
        if main:
            sections.append(
                "<b>真实需求主榜</b>\n" +
                "\n\n".join(_item(o, i + 1) for i, o in enumerate(main))
            )
        if pending:
            start = len(main) + 1
            sections.append(
                "<b>待核验证据副榜（没有原文摘录，不作为商业判断）</b>\n" +
                "\n\n".join(_item(o, start + i) for i, o in enumerate(pending))
            )
        if supply:
            start = len(main) + len(pending) + 1
            sections.append(
                "<b>AI 供给副榜（技术线索，未等于商业机会）</b>\n" +
                "\n\n".join(_item(o, start + i) for i, o in enumerate(supply))
            )
        body = "\n\n".join(sections)
    tail = f"\n\n⚠️ 今天这些源没抓到：{esc('，'.join(missing_sources))}" if missing_sources else ""
    foot = "\n\n<i>想深挖哪条，直接回我「第 N 条」。</i>"
    return f"{head}\n\n{body}{tail}{foot}"


def send_report(opps: list[dict], missing_sources: list[str]) -> None:
    telegram.send_message(render(opps, missing_sources))


def demo() -> None:
    txt = render(
        [{"idea": "示例机会", "verdict": "值得做", "score": 82,
          "reason": "有人已为此付费", "url": "https://example.com", "source": "reddit"}],
        ["producthunt"],
    )
    assert "Top 1" in txt and "示例机会" in txt and "producthunt" in txt
    print("[ok] telegram_report demo 自检通过")


if __name__ == "__main__":
    demo()
