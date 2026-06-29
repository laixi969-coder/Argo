def _has_idea(o):
    """提炼器提不出机会时 idea 为空或「未知」，这类是噪音(新闻/段子/无正文)，不进榜。"""
    idea = str(o.get("idea", "")).strip()
    return idea and idea != "未知"


def rank(opps, n=20):
    kept = [o for o in opps if o.get("verdict") != "伪需求" and _has_idea(o)]
    return sorted(kept, key=lambda o: o.get("score", 0), reverse=True)[:n]
