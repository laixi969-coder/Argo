"""识别已经做出来、能运行或有采用信号的成果。"""

OUTCOME_TYPES = {
    "已有成果产品",
    "可运行 Demo",
    "开源成果",
    "Agent 成果",
    "工业 AI 成果",
}


def is_outcome(opportunity: dict) -> bool:
    return bool(opportunity.get("is_outcome")) or (
        opportunity.get("opportunity_type") in OUTCOME_TYPES
    )
