import json
from concurrent.futures import ThreadPoolExecutor

from src.llm import call_llm
from src import evidence, taxonomy

_CONCURRENCY = 6  # LLM 并发数：压缩总耗时，又不至于把中转站打到限流


PROMPT = """你是「真需求」决策闸门。依据妈妈测试、支付意愿（WTP）和价值→共识→模式闸门，判断下面的产品机会。

三面镜子（命中即伪需求倾向）：玛蒂尔德(自认为有价值但买方不掏钱)、貂丁(每个价值点单看都行凑一起是笑话)、每日优鲜(靠补贴无法从用户获利)。
核心规则：
1. 只能引用给定证据，不得补全、猜测或把源头热度当成付费意愿。
2. 赞美、未来意向和产品 upvote 不是强需求证据；过去行为、反复发生、替代方案、已付成本、预算/预付/付款才是。
3. 证据不足时必须判「待验证」。缺少 WTP、预算或复购数据，只能说明当前材料证据不足，绝不能单独作为「伪需求」反证。
4. 若材料的 evidence_quotes 中有真实定价+付款、付费用户、复购、营收或盈利原句，价值闸门已经通过，判「市场已验证」；market_proof 必须逐字复用其中一条原句。没有该原句一律判「待验证」。
5. 「伪需求」是死刑判定，只能在材料存在明确反证时使用，例如用户明确不需要/拒付、核心承诺无法交付，或单位经济已有证据证明必然倒挂。必须把反证逐字概括进 disproof；没有明确反证就判「待验证」。
6. 无法确定性交付或边际成本可能倒挂时，降低评分并说明；只有已有明确反证时才能判伪需求。
7. 先看需求与支付证据，不预设 AI、互联网、实体、服务哪一种解法更有商业价值。交付范式可以是连接撮合、软件工具、AI 自动交付、实体商品或人工服务；只有材料里的损失、买家和付费证据才能加分。
   - 工作流、模型聚合、易用性、一致性控制本身都可能是用户正在付费的交付价值，不得仅以「工具壳」为由判伪需求；只在排序时降低缺乏壁垒的进入机会分。
   - 关键追问护城河：模型人人能调，凭什么它的交付更好/更便宜？只认三种壁垒——专有数据、工作流深度、品味/审美筛选。三者皆无（纯裸调模型）即降权。
   - 区分「交付效率」（更快更便宜产出同样东西，易被抄平）与「交付质量」（产出人难以企及的东西，更值钱），后者加分。
8. AI 与工业结合、普通软件、实体产品、虚拟内容和服务都同样允许；只要有真实损失、买家与收费路径，均按证据评分，不因技术形态升降权。
9. 可运行 Demo、活跃开源项目和已上线产品只是“已经交付”的采用信号；点赞、Star、Fork、媒体报道都不等于付费，缺少付款/营收时不得判「市场已验证」。
10. 商业潜力只按证据判断：高=已有付款/营收或高频刚需且买家、收费路径清楚；中=痛点成立但支付或获客仍待验证；低=弱需求、低频或商业路径模糊。不得把热度直接写成高潜。
11. 行业与标签必须具体。行业从给定枚举选一个；tags 输出 2-6 个短标签，优先写用户任务、交付形态、收费模式，不写空泛的“AI”“创新”。
12. 可见卡片标题必须写成“机会判断”，不是信息源摘要：用「趋势/变化/能力跃迁 + 受影响用户 + 机会/风险/行动」表达。
    - 好：图生视频进入快预览阶段：内容团队可以低成本批量试镜头再筛选精修
    - 好：Stripe 冻结资金案例：出海平台必须提前设计收款备份和资金风控
    - 坏：Wan2.2 14B Fast Preview、Qwen3-TTS Demo、owner/repo、围绕某项目的 AI 应用机会
    - 技术名词可以保留为背景，但不能当标题主体；如果材料只证明技术热度，标题也要翻译成“谁该关注、为什么该关注”。

待审材料（JSON）：
{evidence}

只输出 JSON，不要任何多余文字：
{{
  "verdict":"市场已验证|真需求|待验证|伪需求",
  "score":0-100整数,
  "category":"实体产品|AI应用|Agent|AI × 工业|虚拟内容|服务|未分类",
  "industry":"制造业|医疗健康|教育|金融|零售电商|营销广告|内容创意|企业服务|开发者工具|法律合规|人力资源|农业|物流供应链|房地产建筑|公共服务|消费生活|跨行业|其他",
  "commercial_potential":"高|中|低",
  "tags":["2-6 个具体短标签"],
  "idea":"机会判断式标题：趋势/变化 + 受影响用户 + 机会/风险/动作；必须中文，不得裸用仓库名/模型名/Demo 名/英文技术描述，未知则写未知",
  "hook":"一句话说清最值得关注的真实损失或交付成果；未知则写未知",
  "pain":"用户正在承受的具体损失；未知则写未知",
  "buyer":"谁有预算并会签字；未知则写未知",
  "money":"可执行的收费方式；未知则写未知",
  "angle":"最小可进入的细分场景；未知则写未知",
  "risk":"最大商业或交付风险；未知则写未知",
  "commercial_evidence":"支持商业潜力的原文证据；没有则写无",
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
        "discovery_theme",
        "industry_hint",
        "source_tags",
        "is_ai_application",
        "evidence_quotes",
    )
    return {field: opp.get(field, "未知") for field in fields}


def _is_listed_quote(opportunity, quote):
    candidate = evidence.normalize(quote)
    return bool(candidate) and any(
        candidate == evidence.normalize(item)
        for item in opportunity.get("evidence_quotes") or []
    )


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


def _judge_error_code(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "timeout" in name or "timeout" in text or "timed out" in text:
        return "judge_timeout"
    if isinstance(exc, json.JSONDecodeError) or "json" in text:
        return "invalid_json"
    if "verdict" in text or "score" in text or "reason" in text:
        return "invalid_judge_result"
    return "judge_failed"


def score_real_demand(opps, llm=call_llm):
    # 逐条独立，可并发；总耗时从「条数×单次」压到约 1/并发数
    with ThreadPoolExecutor(max_workers=_CONCURRENCY) as pool:
        list(pool.map(lambda o: _score_one(o, llm), opps))
    return opps


def _score_one(o, llm):
    try:
        payload = json.dumps(_material(o), ensure_ascii=False, indent=2)
        raw = llm(PROMPT.format(evidence=payload))
        data, score = _parse_result(raw)
        proof = str(data.get("market_proof") or "").strip()
        if data["verdict"] == "市场已验证" and not _is_listed_quote(o, proof):
            data["verdict"] = "待验证"
            data["market_proof"] = "无"
            data["reason"] = f"市场验证证据无法在原文核验，降为待验证：{data.get('reason', '')}"
        o["verdict"] = data["verdict"]
        o["score"] = score
        o["category"] = str(data.get("category") or o.get("category") or "").strip()
        o["industry"] = str(data.get("industry") or o.get("industry") or "").strip()
        o["commercial_potential"] = str(data.get("commercial_potential") or "").strip()
        o["tags"] = taxonomy.normalize_tags(data.get("tags"), o.get("source_tags") or [])
        title = str(data.get("idea") or "").strip()
        if title and title != "未知":
            o["idea"] = title
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
        o["market_proof_verified"] = _is_listed_quote(o, o["market_proof"])
        o["disproof"] = str(data.get("disproof") or "无").strip()
        for field in ("hook", "pain", "buyer", "money", "angle", "risk"):
            o[field] = str(data.get(field) or o.get(field) or "").strip()
        o["commercial_evidence"] = str(
            data.get("commercial_evidence")
            or (o["market_proof"] if o["market_proof"] != "未知" else "无")
        ).strip()
    except Exception as exc:
        o["verdict"] = "待验证"
        o["judge_error"] = _judge_error_code(exc)
        # 源头热度只能决定“值得继续看”，不能冒充真需求或商业潜力。
        # 精判失败时封顶 45，避免高 Star/点赞项目冲到榜首并被误标高潜。
        o["score"] = min(float(o.get("signal", 0)), 45.0)
        o["reason"] = "真需求精判失败，按源头信号保留"
        o["evidence_strength"] = "未知"
        o["next_validation"] = "补采过去行为与真实支付证据"
        o["delivery_edge"] = "未知"
        o["commercial_evidence"] = "无"
        o["commercial_potential"] = "低"
    taxonomy.enrich(o)
