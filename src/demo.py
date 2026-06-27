"""全链路离线演示：不碰任何网络 / key。

用假数据 + 假 LLM 跑通 prefilter→extract→score→rank→render，
写 data/latest_report.json（供 bot 联调）并种入 3 天历史（供 Web 分页/日期分组预览）。

跑：python3 -m src.demo
"""
import json
from datetime import date, timedelta
from pathlib import Path
from src import prefilter, rank, telegram_report, store
from src.extract import extract_ideas
from src.score import score_real_demand

REPORT = Path(__file__).resolve().parent.parent / "data" / "latest_report.json"

# (来源, 标题, 信号, 提炼后的机会, 分, 判定, 分类)
_FAKE = [
    ("reddit", "auto-split freelance invoices", 88, "面向自由职业者的自动发票拆分工具", 84, "真需求", "AI应用"),
    ("producthunt", "AI 会议纪要同步 Notion", 76, "把会议录音自动整理成 Notion 结构纪要", 79, "真需求", "AI应用"),
    ("reddit", "dog-walking scheduler", 64, "社区遛狗排班与拼单小程序", 62, "待验证", "服务"),
    ("producthunt", "跨境多平台库存同步", 59, "给跨境卖家的多平台库存实时同步", 71, "真需求", "实体产品"),
    ("reddit", "voice memo to tasks", 41, "语音备忘自动转结构化待办", 55, "待验证", "AI应用"),
    ("producthunt", "独立站 SEO 内容代写", 47, "面向独立站的 AI SEO 内容批量生成", 49, "伪需求", "虚拟内容"),
]


def _fake_llm(prompt: str) -> str:
    score_stage = "待审材料（JSON）" in prompt
    for src, title, sig, idea, sc, verdict, cat in _FAKE:
        if not score_stage and title in prompt:
            return json.dumps({
                "idea": idea,
                "customer": "自由职业者 / 小团队",
                "job": idea,
                "past_behavior": "每周手工处理并持续抱怨",
                "workaround": "用多个零散工具拼凑",
                "cost_paid": "每周约 3 小时",
                "wtp_evidence": "已购买类似工具",
                "frequency_urgency": "每周发生",
                "missing_evidence": [],
            }, ensure_ascii=False)
        if score_stage and idea in prompt:         # score 阶段：提炼句 → 结构化 JSON
            return json.dumps({
                "verdict": verdict, "score": sc, "category": cat,
                "evidence_strength": "强" if verdict == "真需求" else "中",
                "next_validation": "收取一笔可退预付款验证支付意愿",
                "hook": f"{idea[:18]}——有人一直在抱怨且愿意花钱解决",
                "pain": f"目标用户在「{idea}」这件事上反复手动折腾、耗时易错，吐槽多年却离不开。",
                "buyer": "自由职业者 / 小团队主理人，已有人买零散工具拼凑，月付 30-80 元区间。",
                "money": "SaaS 订阅按席位月付，叠加用量增值包；毛利 85%+，获客后边际成本极低，可随客户成长复利。",
                "angle": "先做最窄的一个动作做到极致，单点切入跑通付费，再横向扩。",
                "risk": "若只是「看着方便」而非刚需，容易沦为伪机会；需先验证有人真掏钱。",
                "reason": (f"判定「{verdict}」：用户省时省钱价值高，"
                           "且已有用户在为类似方案付费，收费模式清晰合理，"
                           "属于「一直吐槽却离不开」的真实痛点，而非「看着挺好没有也行」的自嗨项目。"),
            }, ensure_ascii=False)
    if score_stage:
        return '{"verdict":"待验证","score":50,"reason":"信息不足","evidence_strength":"弱","next_validation":"补采付费证据"}'
    return '{"idea":"某产品机会","missing_evidence":["信息不足"]}'


def _build_day() -> list[dict]:
    opps = [{"source": s, "title": t, "raw_text": t, "url": f"https://example.com/{i}",
             "signal": float(sig)} for i, (s, t, sig, *_ ) in enumerate(_FAKE)]
    top = prefilter.prefilter(opps, n=30)
    top = extract_ideas(top, llm=_fake_llm)
    top = score_real_demand(top, llm=_fake_llm)
    return rank.rank(top, n=20)


def run_demo() -> str:
    final = _build_day()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(final, ensure_ascii=False))
    # 种 3 天历史，让 Web 的日期分组 / 分页有内容
    for d in range(3):
        day = (date.today() - timedelta(days=d)).isoformat()
        store.append(final, day=day)
    return telegram_report.render(final, missing_sources=[])


if __name__ == "__main__":
    print("=" * 60)
    print("Argo 全链路离线演示（假数据，不发网络）")
    print("=" * 60)
    print(run_demo())
    print("=" * 60)
    print(f"[ok] 已写 {REPORT} + 3 天历史（data/history/），可预览 Web")
