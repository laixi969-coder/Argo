from collections import defaultdict
from itertools import zip_longest


def prefilter(opps, n=30):
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
                    return picked
    return picked[:n]
