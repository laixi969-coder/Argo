from src.visibility import is_visible
from src.outcomes import is_outcome


_NO_PROOF = {"", "无", "未知", "没有", "none", "null", "n/a"}


def _has_idea(opportunity):
    """提炼器提不出机会时 idea 为空或「未知」，这类是噪音，不进榜。"""
    idea = str(opportunity.get("idea", "")).strip()
    return idea and idea != "未知"


def _has_paid_market_proof(opportunity):
    """只让可引用的支付证据突破 AI 主榜配额。"""
    proof = str(opportunity.get("market_proof") or "").strip().lower()
    return (
        opportunity.get("verdict") == "市场已验证"
        and opportunity.get("market_proof_verified") is True
        and proof not in _NO_PROOF
    )


def _has_verified_evidence(opportunity):
    return bool(opportunity.get("evidence_quotes"))


def _select_main(ordered, n, min_product_pool, min_industry_pool):
    """在已获准进入主榜的候选中保留成果与行业多样性席位。"""
    products = [opportunity for opportunity in ordered if is_outcome(opportunity)]
    reserved = products[:min(min_product_pool, n)]
    reserved_ids = {id(opportunity) for opportunity in reserved}
    reserved_industries = {
        opportunity.get("industry") for opportunity in reserved
        if opportunity.get("industry") not in {None, "", "跨行业", "其他"}
    }
    for opportunity in ordered:
        industry = opportunity.get("industry")
        if len(reserved_industries) >= min_industry_pool or len(reserved) >= n:
            break
        if id(opportunity) in reserved_ids or industry in {None, "", "跨行业", "其他"}:
            continue
        if industry in reserved_industries:
            continue
        reserved.append(opportunity)
        reserved_ids.add(id(opportunity))
        reserved_industries.add(industry)
    remainder = [opportunity for opportunity in ordered if id(opportunity) not in reserved_ids]
    final = reserved + remainder[:max(0, n - len(reserved))]
    return sorted(final, key=lambda opportunity: opportunity.get("score", 0), reverse=True)


def rank(opps, n=20, min_product_pool=6, min_industry_pool=5, ai_share=0.4):
    """生成「真实需求主榜」与明确标注的 AI 供给副榜。

    AI 是解法，不是商业性本身：没有可引用付款/营收证据的 AI 候选在
    主榜最多占 ``ai_share``，其余仍保留在副榜供研究，但不会伪装成商业
    机会。已有市场验证的 AI 候选不受此配额限制。
    """
    kept = [
        opportunity for opportunity in opps
        if (opportunity.get("verdict") != "伪需求"
            and _has_idea(opportunity)
            and is_visible(opportunity))
    ]
    ordered = sorted(kept, key=lambda opportunity: opportunity.get("score", 0), reverse=True)
    ai_unverified = [
        opportunity for opportunity in ordered
        if (opportunity.get("is_ai_application") is True
            and not _has_paid_market_proof(opportunity))
    ]
    # 按当天实际可入榜条数配额：候选不足 20 条时也不能让 AI 占比失控。
    available_slots = min(n, len(ordered))
    main_capacity = max(0, int(available_slots * ai_share))
    allowed_ai_ids = {id(opportunity) for opportunity in ai_unverified[:main_capacity]}
    main_candidates = [
        opportunity for opportunity in ordered
        if (_has_verified_evidence(opportunity)
            and (opportunity.get("is_ai_application") is not True
            or _has_paid_market_proof(opportunity)
            or id(opportunity) in allowed_ai_ids))
    ]
    main = _select_main(main_candidates, n, min_product_pool, min_industry_pool)
    main_ids = {id(opportunity) for opportunity in main}
    for opportunity in main:
        opportunity["radar_track"] = "真实需求主榜"

    # 没有可核验原文的线索绝不进入主榜；仍保留在副榜供人工复查。
    side = [opportunity for opportunity in ordered if id(opportunity) not in main_ids]
    side = side[:max(0, n - len(main))]
    for opportunity in side:
        opportunity["radar_track"] = (
            "AI 供给副榜" if opportunity.get("is_ai_application") is True
            else "待核验证据副榜"
        )
    return main + side
