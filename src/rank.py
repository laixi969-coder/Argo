from src.visibility import is_visible
from src.outcomes import is_outcome


def _has_idea(o):
    """提炼器提不出机会时 idea 为空或「未知」，这类是噪音(新闻/段子/无正文)，不进榜。"""
    idea = str(o.get("idea", "")).strip()
    return idea and idea != "未知"


def rank(opps, n=20, min_product_pool=6, min_industry_pool=5):
    """排序并为已做出成果的产品保留研究席位。

    成果产品仍须通过 30 分硬门槛；保留席位只防止它们被更高热度的
    痛点帖子全部挤掉，不会让低质量结果绕过真需求闸门。
    """
    kept = [
        o for o in opps
        if o.get("verdict") != "伪需求" and _has_idea(o) and is_visible(o)
    ]
    ordered = sorted(kept, key=lambda o: o.get("score", 0), reverse=True)
    products = [o for o in ordered if is_outcome(o)]
    reserved = products[:min(min_product_pool, n)]
    reserved_ids = {id(o) for o in reserved}
    reserved_industries = {
        o.get("industry") for o in reserved
        if o.get("industry") not in {None, "", "跨行业", "其他"}
    }
    for o in ordered:
        industry = o.get("industry")
        if len(reserved_industries) >= min_industry_pool or len(reserved) >= n:
            break
        if id(o) in reserved_ids or industry in {None, "", "跨行业", "其他"}:
            continue
        if industry in reserved_industries:
            continue
        reserved.append(o)
        reserved_ids.add(id(o))
        reserved_industries.add(industry)
    remainder = [o for o in ordered if id(o) not in reserved_ids]
    final = reserved + remainder[:max(0, n - len(reserved))]
    return sorted(final, key=lambda o: o.get("score", 0), reverse=True)
