import json
import urllib.request
from src import config
from src.visibility import visible_only


def _card(opps: list[dict], missing_sources: list[str]) -> dict:
    """渲染飞书交互卡片：标题 + 每条机会一段 + 缺源提醒。"""
    opps = visible_only(opps)
    if not opps:
        lines = ["**今日无机会入榜。**"]
    else:
        lines = [
            f"**{i + 1}. [{o['idea']}]({o['url']})**  ·  "
            f"{o['verdict']} · {int(o['score'])}分 · {o['source']}\n"
            f"{o.get('commercial_potential', '')}商业潜力 · {o.get('industry', '跨行业')} · "
            f"{' '.join('#' + str(t) for t in o.get('tags', [])[:3])}\n"
            f"{o['reason']}"
            for i, o in enumerate(opps)
        ]
    if missing_sources:
        lines.append(f"<font color='red'>今天这些源没抓到：{', '.join(missing_sources)}</font>")

    elements = []
    for line in lines:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})
        elements.append({"tag": "hr"})
    elements.pop() if elements else None  # 去掉末尾多余分隔线

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"金羊毛 Argo · 今日选品 Top {len(opps)}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def send_report(opps: list[dict], missing_sources: list[str]) -> None:
    webhook = config.get("FEISHU_WEBHOOK")
    if not webhook:
        raise RuntimeError("FEISHU_WEBHOOK 未配置，无法推送飞书")
    data = json.dumps(_card(opps, missing_sources)).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
    # 飞书成功返回 code=0；非 0 抛错，不让流水线静默吞掉
    if body.get("code") not in (0, None):
        raise RuntimeError(f"飞书推送失败: {body}")


def demo() -> None:
    """自检：不发网络，只验证卡片结构正确。"""
    card = _card(
        [{"idea": "示例机会", "verdict": "值得做", "score": 82,
          "reason": "有人已为此付费", "url": "https://example.com", "source": "reddit"}],
        ["producthunt"],
    )
    assert card["msg_type"] == "interactive"
    assert "Top 1" in card["card"]["header"]["title"]["content"]
    assert any("示例机会" in e.get("text", {}).get("content", "") for e in card["card"]["elements"])
    assert any("producthunt" in e.get("text", {}).get("content", "") for e in card["card"]["elements"])
    print("[ok] feishu_report demo 自检通过")


if __name__ == "__main__":
    demo()
