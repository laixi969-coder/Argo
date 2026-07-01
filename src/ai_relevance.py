"""AI 应用相关性硬门槛。"""

_AI_NATIVE_SOURCES = {"huggingface", "github", "futurepedia", "industry_cases"}
_TERMS = (
    " ai ", "ai-", "ai_", "artificial intelligence", "agent", "llm", "gpt",
    "machine learning", "computer vision", "neural", "generative", "copilot",
    "大模型", "人工智能", "智能体", "机器学习", "计算机视觉", "生成式",
    "模型推理", "多模态", "自动化工作流",
)


def infer(opportunity: dict) -> bool:
    if opportunity.get("source") in _AI_NATIVE_SOURCES:
        return True
    text = " ".join(str(opportunity.get(k) or "") for k in (
        "idea", "title", "raw_text", "job", "discovery_theme", "opportunity_type",
    )).lower()
    padded = f" {text} "
    return any(term in padded for term in _TERMS)
