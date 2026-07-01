"""Argo 统一分类、行业与商业潜力标签。"""

from src.ai_relevance import infer as infer_ai_relevance

CATEGORIES = (
    "实体产品", "AI应用", "Agent", "AI × 工业", "虚拟内容", "服务",
)

INDUSTRIES = (
    "制造业", "医疗健康", "教育", "金融", "零售电商", "营销广告",
    "内容创意", "企业服务", "开发者工具", "法律合规", "人力资源",
    "农业", "物流供应链", "房地产建筑", "公共服务", "消费生活",
    "跨行业", "其他",
)

COMMERCIAL_POTENTIALS = ("高", "中", "低")

_INDUSTRY_TERMS = (
    ("制造业", ("工厂", "制造", "产线", "设备", "质检", "工业", "machine vision",
              "manufactur", "factory", "predictive maintenance")),
    ("医疗健康", ("医疗", "医生", "患者", "医院", "健康", "medical", "healthcare")),
    ("教育", ("教育", "教师", "学生", "课程", "学习", "education", "teacher", "student")),
    ("金融", ("金融", "银行", "保险", "发票", "财务", "会计", "finance", "invoice", "accounting")),
    ("零售电商", ("零售", "电商", "商店", "库存", "retail", "ecommerce", "e-commerce")),
    ("营销广告", ("营销", "广告", "投放", "增长", "marketing", "advertis")),
    ("内容创意", ("视频", "图像", "设计", "音乐", "创意", "video", "image", "design", "music")),
    ("开发者工具", ("代码", "编程", "开发者", "github", "coding", "developer", "api")),
    ("法律合规", ("法律", "合同", "合规", "律师", "legal", "contract", "compliance")),
    ("人力资源", ("招聘", "员工", "人力资源", "面试", "recruit", "human resources", "hr ")),
    ("农业", ("农业", "农场", "作物", "agriculture", "farm", "crop")),
    ("物流供应链", ("物流", "供应链", "运输", "仓储", "logistics", "supply chain", "warehouse")),
    ("房地产建筑", ("房地产", "建筑", "施工", "物业", "construction", "real estate")),
    ("公共服务", ("政府", "政务", "公共服务", "government", "public sector")),
    ("企业服务", ("企业", "团队", "工作流", "办公", "enterprise", "workflow", "saas")),
    ("消费生活", ("宠物", "家庭", "个人", "旅行", "生活", "consumer", "personal", "travel")),
)


def infer_industry(text: str) -> str:
    haystack = str(text or "").lower()
    for industry, terms in _INDUSTRY_TERMS:
        if any(term in haystack for term in terms):
            return industry
    return "跨行业"


def normalize_tags(value, fallback=()) -> list[str]:
    values = value if isinstance(value, list) else fallback
    out = []
    for item in values or ():
        tag = str(item or "").strip().lstrip("#")[:24]
        if tag and tag not in out and tag not in {"未知", "未分类"}:
            out.append(tag)
        if len(out) >= 6:
            break
    return out


def _potential(score, verdict: str) -> str:
    try:
        number = float(score)
    except (TypeError, ValueError):
        number = 0
    if verdict == "市场已验证" or number >= 80:
        return "高"
    if number >= 60:
        return "中"
    return "低"


def enrich(opportunity: dict) -> dict:
    """为成功与降级路径都补齐稳定字段，避免展示层猜结构。"""
    theme = str(opportunity.get("discovery_theme") or "")
    if not isinstance(opportunity.get("is_ai_application"), bool):
        opportunity["is_ai_application"] = infer_ai_relevance(opportunity)
    category = str(opportunity.get("category") or "").strip()
    if category not in CATEGORIES:
        category = "Agent" if "Agent" in theme else (
            "AI × 工业" if "工业" in theme else "AI应用"
        )
    opportunity["category"] = category

    industry = str(opportunity.get("industry") or opportunity.get("industry_hint") or "").strip()
    if industry not in INDUSTRIES:
        text = " ".join(str(opportunity.get(k) or "") for k in (
            "idea", "title", "raw_text", "job", "customer", "discovery_theme",
        ))
        industry = infer_industry(text)
    if category == "AI × 工业" and industry == "跨行业":
        industry = "制造业"
    opportunity["industry"] = industry

    failed_judgement = str(opportunity.get("reason") or "").startswith("真需求精判失败")
    if failed_judgement:
        try:
            opportunity["score"] = min(float(opportunity.get("score", 0)), 45.0)
        except (TypeError, ValueError):
            opportunity["score"] = 0.0
        opportunity["commercial_potential"] = "低"

    potential = str(opportunity.get("commercial_potential") or "").strip()
    if potential not in COMMERCIAL_POTENTIALS:
        potential = _potential(opportunity.get("score"), str(opportunity.get("verdict") or ""))
    opportunity["commercial_potential"] = potential

    fallback_tags = [
        *(opportunity.get("source_tags") or []),
        category,
        industry if industry != "跨行业" else "",
        opportunity.get("opportunity_type") or "",
    ]
    tags = normalize_tags(opportunity.get("tags"), fallback_tags)
    opportunity["tags"] = tags or [category]
    return opportunity
