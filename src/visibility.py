"""机会对外展示的统一门槛。"""

MIN_DISPLAY_SCORE = 30


def is_visible(opportunity: dict) -> bool:
    try:
        return (
            opportunity.get("is_ai_application") is not False
            and float(opportunity.get("score", 0)) >= MIN_DISPLAY_SCORE
        )
    except (TypeError, ValueError):
        return False


def visible_only(opportunities):
    return [o for o in opportunities if is_visible(o)]
