"""商业机会对外展示的统一门槛。"""

MIN_DISPLAY_SCORE = 30


def is_visible(opportunity: dict) -> bool:
    """按真需求评分展示，而不是按是否 AI 展示。

    AI 是一个机会分类，实体、服务与内容只要通过同样的证据门槛，也应被
    创业者看见。
    """
    try:
        return float(opportunity.get("score", 0)) >= MIN_DISPLAY_SCORE
    except (TypeError, ValueError):
        return False


def visible_only(opportunities):
    return [o for o in opportunities if is_visible(o)]
