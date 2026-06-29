"""渲染并推送每日榜单到 Telegram（HTML 模式，动态字段全转义）。

接口与原邮件模块一致：send_report(opps, missing)。
"""
from src import telegram

esc = telegram.esc


def _edge(o: dict) -> str:
    """交付范式标签：有值且非「未知」才显示，老数据无此字段不报错。"""
    edge = str(o.get("delivery_edge", "") or "").strip()
    return f" · 🎯{esc(edge)}" if edge and edge != "未知" else ""


def render(opps: list[dict], missing_sources: list[str]) -> str:
    head = f"<b>金羊毛 Argo · 今日选品 Top {len(opps)}</b>"
    if not opps:
        body = "今日无机会入榜。"
    else:
        body = "\n\n".join(
            f"<b>{i + 1}. {esc(o['idea'])}</b>\n"
            f"{esc(o['verdict'])} · {int(o['score'])}分 · "
            f"<a href=\"{esc(o['url'])}\">{esc(o['source'])}</a>"
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
