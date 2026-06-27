import json

from src.llm import call_llm


PROMPT = """你是「真需求」决策闸门。依据妈妈测试、支付意愿（WTP）和价值→共识→模式闸门，判断下面的产品机会。

三面镜子（命中即伪需求倾向）：玛蒂尔德(自认为有价值但买方不掏钱)、貂丁(每个价值点单看都行凑一起是笑话)、每日优鲜(靠补贴无法从用户获利)。
核心规则：
1. 只能引用给定证据，不得补全、猜测或把源头热度当成付费意愿。
2. 赞美、未来意向和产品 upvote 不是强需求证据；过去行为、反复发生、替代方案、已付成本、预算/预付/付款才是。
3. 证据不足时必须判「待验证」，不能仅凭点子听起来合理就判「真需求」。
4. 无法确定性交付或边际成本可能倒挂时，降低评分并说明。

待审材料（JSON）：
{evidence}

只输出 JSON，不要任何多余文字：
{{
  "verdict":"真需求|待验证|伪需求",
  "score":0-100整数,
  "reason":"一句话说明最强证据和最大缺口",
  "evidence_strength":"强|中|弱",
  "next_validation":"一个可验证真实支付意愿的最小动作"
}}"""

VALID_VERDICTS = {"真需求", "待验证", "伪需求"}
VALID_EVIDENCE_STRENGTH = {"强", "中", "弱"}


def _material(opp):
    fields = (
        "idea",
        "customer",
        "job",
        "past_behavior",
        "workaround",
        "cost_paid",
        "wtp_evidence",
        "frequency_urgency",
        "missing_evidence",
        "source",
        "signal",
    )
    return {field: opp.get(field, "未知") for field in fields}


def _parse_result(raw):
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response contains no JSON object")
    data = json.loads(raw[start:end + 1])
    if data.get("verdict") not in VALID_VERDICTS:
        raise ValueError("invalid verdict")
    score = float(data["score"])
    if not 0 <= score <= 100:
        raise ValueError("score outside 0-100")
    reason = str(data.get("reason", "")).strip()
    if not reason:
        raise ValueError("missing reason")
    return data, score


def score_real_demand(opps, llm=call_llm):
    for o in opps:
        try:
            evidence = json.dumps(_material(o), ensure_ascii=False, indent=2)
            raw = llm(PROMPT.format(evidence=evidence))
            data, score = _parse_result(raw)
            o["verdict"] = data["verdict"]
            o["score"] = score
            o["reason"] = str(data["reason"]).strip()
            strength = data.get("evidence_strength", "未知")
            o["evidence_strength"] = (
                strength if strength in VALID_EVIDENCE_STRENGTH else "未知"
            )
            o["next_validation"] = str(
                data.get("next_validation") or "补采过去行为与真实支付证据"
            ).strip()
        except Exception:
            o["verdict"] = "待验证"
            o["score"] = float(o.get("signal", 0))
            o["reason"] = "真需求精判失败，按源头信号保留"
            o["evidence_strength"] = "未知"
            o["next_validation"] = "补采过去行为与真实支付证据"
    return opps
