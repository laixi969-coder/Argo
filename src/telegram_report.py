"""渲染并推送每日榜单到 Telegram（HTML 模式，动态字段全转义）。

接口与原邮件模块一致：send_report(opps, missing)。
"""
from src import telegram

esc = telegram.esc

# 显示用的源名（合并细分变体到大名字），只影响展示，不动内部 source 值
_SOURCE_LABELS = {
    "reddit_tikhub": "Reddit",
    "reddit_comments_tikhub": "Reddit",
    "reddit": "Reddit",
    "producthunt": "Product Hunt",
    "hackernews": "Hacker News",
    "tikhub": "TikTok",
}


def _label(source: str) -> str:
    return _SOURCE_LABELS.get(source, source)


def _edge(o: dict) -> str:
    """交付范式 + 操盘手契合标签：有值且非「未知」才显示，老数据无此字段不报错。"""
    tags = ""
    edge = str(o.get("delivery_edge", "") or "").strip()
    if edge and edge != "未知":
        tags += f" · 🎯{esc(edge)}"
    fit = str(o.get("edge_fit", "") or "").strip()
    if fit and fit != "未知":
        # edge_fit 形如「高，理由…」，标签只取等级首段，理由进正文太长
        level = fit.split("，")[0].split(",")[0].strip()
        tags += f" · 🧭契合{esc(level)}"
    return tags


def render(opps: list[dict], missing_sources: list[str]) -> str:
    head = f"<b>金羊毛 Argo · 今日选品 Top {len(opps)}</b>"
    if not opps:
        body = "今日无机会入榜。"
    else:
        body = "\n\n".join(
            f"<b>{i + 1}. {esc(o['idea'])}</b>\n"
            f"{esc(o['verdict'])} · {int(o['score'])}分 · "
            f"<a href=\"{esc(o['url'])}\">{esc(_label(o['source']))}</a>"
            f"{_edge(o)}\n"
            f"{esc(o['reason'])}"
            for i, o in enumerate(opps)
        )
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
