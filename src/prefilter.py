from collections import defaultdict
from itertools import zip_longest
from src.outcomes import is_outcome


def prefilter(opps, n=30, min_product_pool=15, min_industry_pool=10):
    """源公平粗筛：各源内部按 signal 排序后轮流入选，保证每个源都有名额，
    避免某个源(如 Reddit 赞数易顶满 100)靠并列高分霸榜、挤掉其它源。
    名额没填满时按全局 signal 补齐。
    """
    by_source = defaultdict(list)
    for o in opps:
        by_source[o.get("source", "")].append(o)
    for items in by_source.values():
        items.sort(key=lambda o: o.get("signal", 0), reverse=True)

    # 轮流从各源取最强的一条，循环往复
    picked, seen = [], set()
    for tier in zip_longest(*by_source.values()):
        for o in tier:
            if o is not None and id(o) not in seen:
                picked.append(o)
                seen.add(id(o))
                if len(picked) >= n:
                    break
        if len(picked) >= n:
            break

    # 产品目录/Show HN 属于“已有解法”证据，信号分通常不如痛点帖热度高。
    # 为它们预留进入精判的候选席位，避免在昂贵 LLM 判断前就被挤光。
    products = sorted(
        (o for o in opps if is_outcome(o)),
        key=lambda o: o.get("signal", 0), reverse=True,
    )
    required = min(min_product_pool, n, len(products))
    selected_products = sum(
        is_outcome(o) for o in picked
    )
    selected_ids = {id(o) for o in picked}
    for product in products:
        if selected_products >= required:
            break
        if id(product) in selected_ids:
            continue
        replaceable = [
            (i, o) for i, o in enumerate(picked)
            if not is_outcome(o)
        ]
        if not replaceable:
            break
        index, removed = min(replaceable, key=lambda pair: pair[1].get("signal", 0))
        picked[index] = product
        selected_ids.discard(id(removed))
        selected_ids.add(id(product))
        selected_products += 1

    # 行业专线按行业各取最强一条，避免医疗/法律等单一高热度行业占满席位。
    industry_best = {}
    for o in opps:
        industry = str(o.get("industry_hint") or "").strip()
        if not industry or industry in {"跨行业", "其他"}:
            continue
        current = industry_best.get(industry)
        if current is None or o.get("signal", 0) > current.get("signal", 0):
            industry_best[industry] = o
    industry_candidates = sorted(
        industry_best.values(), key=lambda o: o.get("signal", 0), reverse=True,
    )[:min_industry_pool]
    selected_industries = {
        o.get("industry_hint") for o in picked if o.get("industry_hint")
    }
    for candidate in industry_candidates:
        industry = candidate.get("industry_hint")
        if industry in selected_industries or id(candidate) in selected_ids:
            continue
        replaceable = [
            (i, o) for i, o in enumerate(picked)
            if not is_outcome(o) and not o.get("industry_hint")
        ]
        if not replaceable:
            break
        index, removed = min(replaceable, key=lambda pair: pair[1].get("signal", 0))
        picked[index] = candidate
        selected_ids.discard(id(removed))
        selected_ids.add(id(candidate))
        selected_industries.add(industry)
    return picked[:n]
