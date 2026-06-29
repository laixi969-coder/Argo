import json
import re

from src.llm import call_llm

# 从坏 JSON（如内部引号未转义解析失败）里捞出 idea 那句话，避免把整坨原文塞进展示
_IDEA_RE = re.compile(r'"idea"\s*:\s*"(.+?)"\s*[,}\n]', re.DOTALL)


def _salvage_idea(raw, fallback):
    m = _IDEA_RE.search(raw)
    idea = m.group(1).strip() if m else ""
    # 捞出来的内容若仍像 JSON 残片（含大括号/多个字段），不可信，退回标题
    if idea and "{" not in idea and '":' not in idea:
        return idea
    return fallback


PROMPT = """你是产品机会的证据提取器。只根据原文提取事实，不评价机会好坏，也绝不补全原文没有的信息。

妈妈测试规则：赞美、未来意向和“这个点子不错”不算需求证据；优先寻找过去真实发生的行为、当前替代方案、已经付出的时间/金钱，以及明确的求购、预算、预付或付款记录。

标题：{title}
正文：{text}

只输出合法 JSON：
{{
  "idea": "一句话产品机会（谁的什么任务 + 什么产品）",
  "customer": "原文明示的用户；没有则写未知",
  "job": "用户要完成的现实任务；没有则写未知",
  "past_behavior": "过去实际发生的行为；没有则写未知",
  "workaround": "当前替代方案；没有则写未知",
  "cost_paid": "已经付出的金钱或时间；没有则写未知",
  "wtp_evidence": "明确求购、预算、预付或付款证据；没有则写未知",
  "frequency_urgency": "发生频率与紧迫度；没有则写未知",
  "missing_evidence": ["仍缺少、且会影响判断的关键证据"]
}}"""

EVIDENCE_FIELDS = (
    "customer",
    "job",
    "past_behavior",
    "workaround",
    "cost_paid",
    "wtp_evidence",
    "frequency_urgency",
)


def _parse_json(raw):
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response contains no JSON object")
    data = json.loads(raw[start:end + 1])
    if not isinstance(data, dict) or not str(data.get("idea", "")).strip():
        raise ValueError("missing idea")
    return data


def _evidence_summary(opp):
    labels = {
        "past_behavior": "历史行为",
        "workaround": "现有替代",
        "cost_paid": "已付成本",
        "wtp_evidence": "付费证据",
        "frequency_urgency": "频率/紧迫度",
    }
    facts = []
    for field, label in labels.items():
        value = str(opp.get(field, "")).strip()
        if value and value != "未知":
            facts.append(f"{label}：{value}")
    return "；".join(facts) if facts else "未发现可核验的行为或付费证据"


def extract_ideas(opps, llm=call_llm):
    for o in opps:
        try:
            raw = llm(
                PROMPT.format(
                    title=o.get("title", ""),
                    text=o.get("raw_text", "")[:3000],
                )
            ).strip()
            try:
                data = _parse_json(raw)
            except (ValueError, json.JSONDecodeError):
                # 解析失败：可能是一句话输出，也可能是坏 JSON。
                # 坏 JSON 时只捞 idea 句子，绝不把整坨原文当 idea 显示。
                title = o.get("title", "")
                o["idea"] = _salvage_idea(raw, title) if "{" in raw else (raw or title)
                for field in EVIDENCE_FIELDS:
                    o[field] = "未知"
                o["missing_evidence"] = ["结构化证据提取失败"]
            else:
                o["idea"] = str(data["idea"]).strip()
                for field in EVIDENCE_FIELDS:
                    o[field] = str(data.get(field) or "未知").strip()
                missing = data.get("missing_evidence", [])
                o["missing_evidence"] = (
                    [str(item).strip() for item in missing if str(item).strip()]
                    if isinstance(missing, list)
                    else [str(missing).strip()]
                )
        except Exception:
            o["idea"] = o.get("title", "")
            for field in EVIDENCE_FIELDS:
                o[field] = "未知"
            o["missing_evidence"] = ["证据提取调用失败"]
        o["demand_evidence"] = _evidence_summary(o)
    return opps
