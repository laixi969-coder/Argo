import json
from concurrent.futures import ThreadPoolExecutor

from src.llm import call_llm

_CONCURRENCY = 6  # LLM 并发数：压缩总耗时，又不至于把中转站打到限流


PROMPT = """你是「真需求」决策闸门。依据妈妈测试、支付意愿（WTP）和价值→共识→模式闸门，判断下面的产品机会。

三面镜子（命中即伪需求倾向）：玛蒂尔德(自认为有价值但买方不掏钱)、貂丁(每个价值点单看都行凑一起是笑话)、每日优鲜(靠补贴无法从用户获利)。
核心规则：
1. 只能引用给定证据，不得补全、猜测或把源头热度当成付费意愿。
2. 赞美、未来意向和产品 upvote 不是强需求证据；过去行为、反复发生、替代方案、已付成本、预算/预付/付款才是。
3. 证据不足时必须判「待验证」。缺少 WTP、预算或复购数据，只能说明当前材料证据不足，绝不能单独作为「伪需求」反证。
4. 若材料明确出现真实定价+付款、付费用户、复购、营收或盈利，价值闸门已经通过，判「市场已验证」；之后只评价进入机会与护城河，不得倒判伪需求。
5. 「伪需求」是死刑判定，只能在材料存在明确反证时使用，例如用户明确不需要/拒付、核心承诺无法交付，或单位经济已有证据证明必然倒挂。必须把反证逐字概括进 disproof；没有明确反证就判「待验证」。
6. 无法确定性交付或边际成本可能倒挂时，降低评分并说明；只有已有明确反证时才能判伪需求。
7. 交付范式（区分机会代际）：互联网产品赢在「连接效率」（撮合供需后抽成，护城河=网络效应，如滴滴连人车、淘宝连人货）；AI 产品赢在「高质量交付效率」（自己把活干出来——出片/代码/文案/分析）。
   - 工作流、模型聚合、易用性、一致性控制本身都可能是用户正在付费的交付价值，不得仅以「工具壳」为由判伪需求；只在排序时降低缺乏壁垒的进入机会分。
   - 关键追问护城河：模型人人能调，凭什么它的交付更好/更便宜？只认三种壁垒——专有数据、工作流深度、品味/审美筛选。三者皆无（纯裸调模型）即降权。
   - 区分「交付效率」（更快更便宜产出同样东西，易被抄平）与「交付质量」（产出人难以企及的东西，更值钱），后者加分。

待审材料（JSON）：
{evidence}

只输出 JSON，不要任何多余文字：
{{
  "verdict":"市场已验证|真需求|待验证|伪需求",
  "score":0-100整数,
  "reason":"一句话说明最强证据和最大缺口",
  "evidence_strength":"强|中|弱",
  "delivery_edge":"高质量交付|连接撮合|工具壳|不适用，并指出护城河有无",
  "market_proof":"引用材料中的付费/复购/营收/盈利证据；没有则写无",
  "disproof":"仅在判伪需求时写明确反证；其他情况写无",
  "next_validation":"一个可验证真实支付意愿的最小动作"
}}"""

VALID_VERDICTS = {"市场已验证", "真需求", "待验证", "伪需求"}
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
        "market_proof",
        "frequency_urgency",
        "missing_evidence",
        "source",
        "signal",
        "opportunity_type",
        "published_at",
    )
    return {field: opp.get(field, "未知") for field in fields}


def _parse_result(raw):
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response contains no JSON object")
    data = json.loads(raw[start:end + 1])
    if data.get("verdict") not in VALID_VERDICTS:
        raise ValueError("invalid verdict")
    verdict = data["verdict"]
    market_proof = str(data.get("market_proof") or "").strip()
    disproof = str(data.get("disproof") or "").strip()
    missing = {"", "无", "未知", "没有", "none", "null", "n/a"}
    if verdict == "市场已验证" and market_proof.lower() in missing:
        data["verdict"] = "待验证"
        data["reason"] = f"缺少可引用的市场验证证据，降为待验证：{data.get('reason', '')}"
    if verdict == "伪需求" and disproof.lower() in missing:
        data["verdict"] = "待验证"
        data["reason"] = f"缺少明确反证，降为待验证：{data.get('reason', '')}"
    score = float(data["score"])
    if verdict == "伪需求" and data["verdict"] == "待验证":
        score = max(score, 40)
    if not 0 <= score <= 100:
        raise ValueError("score outside 0-100")
    reason = str(data.get("reason", "")).strip()
    if not reason:
        raise ValueError("missing reason")
    return data, score


def score_real_demand(opps, llm=call_llm):
    # 逐条独立，可并发；总耗时从「条数×单次」压到约 1/并发数
    with ThreadPoolExecutor(max_workers=_CONCURRENCY) as pool:
        list(pool.map(lambda o: _score_one(o, llm), opps))
    return opps


def _score_one(o, llm):
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
        o["delivery_edge"] = str(data.get("delivery_edge") or "未知").strip()
        o["market_proof"] = str(data.get("market_proof") or o.get("market_proof") or "未知").strip()
        o["disproof"] = str(data.get("disproof") or "无").strip()
    except Exception:
        o["verdict"] = "待验证"
        o["score"] = float(o.get("signal", 0))
        o["reason"] = "真需求精判失败，按源头信号保留"
        o["evidence_strength"] = "未知"
        o["next_validation"] = "补采过去行为与真实支付证据"
        o["delivery_edge"] = "未知"
