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


def business_stage(opportunity: dict) -> str:
    """把「有信号」与「可能是好生意」明确分开。"""
    verdict = str(opportunity.get("verdict") or "").strip()
    if verdict == "伪需求":
        return "止损"
    if (verdict == "市场已验证"
            and opportunity.get("commercial_potential") == "高"
            and opportunity.get("evidence_strength") == "强"
            and str(opportunity.get("market_proof") or "").strip() not in {"", "无", "未知"}):
        return "好生意候选"
    if verdict == "市场已验证":
        return "已验证市场"
    if verdict == "真需求":
        return "可小试"
    return "发现线索"

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


def _plain_chinese_title(opportunity: dict, category: str, industry: str) -> str:
    idea = str(opportunity.get("idea") or "").strip()
    title = str(opportunity.get("title") or "").strip()
    text = _title_context(opportunity)

    if idea and not _needs_title_rewrite(idea, opportunity):
        return idea

    if any(word in text for word in ("stripe", "withheld", "freeze", "frozen", "冻结", "扣款")):
        return "Stripe 冻结资金案例：出海平台必须提前设计收款备份和资金风控"
    if any(word in text for word in ("tts", "text to speech", "语音合成", "配音")):
        return "中文 TTS 成本继续下降：品牌声音、短视频配音和 AI 客服开始适合小团队试水"
    if any(word in text for word in ("gpu", "cuda", "ai-fundamentals", "ai fundamentals", "基础知识")):
        return "AI 基础知识正在变成创业判断力：不懂 GPU、CUDA、Agent，就很难判断项目成本"
    if "windsurf" in text or " ide " in f" {text} ":
        return "IDE 编程助手从补全走向交付：开发者需要能理解项目并可靠改代码的工具"
    if any(word in text for word in ("oh-my-pi", "terminal", "lsp", "hash-anchored")):
        return "终端 AI 编程助手继续进化：可靠代码定位、浏览器操作和多 Agent 协作成为标配"
    if any(word in text for word in ("wan2.2", "image to video", "图生视频")):
        return "图生视频进入快预览阶段：内容团队可以低成本批量试镜头再筛选精修"
    if "motion comic" in text or "short film" in text or "短片漫画" in text:
        return "AI 短片漫画生成开始产品化：内容团队可以把分镜资产直接压成可验证样片"
    if any(word in text for word in ("storyboard", "分镜", "video workflow", "视频工作台")):
        return "内容团队最缺的不是模型，而是分镜、图生视频和多版本管理的生产工作台"
    if any(word in text for word in ("code", "coding", "developer", "代码", "编程", "jcode")):
        return "AI 编程工具需要重点看：它是否解决准确改代码和团队可控交付问题"
    if any(word in text for word in ("mcp", "agent", "orchestrator", "workflow", "dashboard")):
        return "AI Agent 从单人玩具走向团队协作：任务编排、权限、日志和交付追踪会成为刚需"
    if category == "AI × 工业" or (industry == "制造业" and opportunity.get("is_ai_application") is True):
        return "工业 AI 的机会在降本而非炫技：制造团队会为停机、良率和能耗改善付费"
    if industry != "跨行业":
        prefix = "AI " if opportunity.get("is_ai_application") is True else ""
        return f"{industry}团队的 {prefix}机会：先找高频损失场景，再验证付费意愿"
    if title:
        return ("新 AI 工具信号：先判断它替代哪段人工、谁会付费和能否持续交付"
                if opportunity.get("is_ai_application") is True else
                "新商业信号：先判断谁在承担损失、谁会付费和能否持续交付")
    return ("一个待验证的 AI 应用机会：先确认用户痛点、预算和最小付费动作"
            if opportunity.get("is_ai_application") is True else
            "一个待验证的商业机会：先确认用户痛点、预算和最小付费动作")


def _title_context(opportunity: dict) -> str:
    parts = []
    for key in (
        "idea", "title", "raw_text", "opportunity_type", "discovery_theme",
        "job", "customer", "hook", "pain", "buyer", "angle", "risk",
    ):
        parts.append(str(opportunity.get(key) or ""))
    parts.extend(str(tag or "") for tag in opportunity.get("source_tags") or [])
    return " ".join(parts).lower()


def _needs_title_rewrite(idea: str, opportunity: dict) -> bool:
    generic = idea.startswith("围绕「") or idea in {"未知", "某产品机会"}
    if generic:
        return True
    if _has_chinese_judgement(idea):
        return False
    head = idea.split("：", 1)[0]
    source = str(opportunity.get("source") or "").lower()
    repo_like = _looks_like_repo_slug(head) or (
        source in {"github", "huggingface"} and _mostly_english(idea)
    )
    technical_label = _mostly_english(idea) or any(
        word in idea.lower() for word in ("demo", "preview", "github", "huggingface")
    )
    return repo_like or technical_label


def _has_chinese_judgement(value: str) -> bool:
    if not any("一" <= ch <= "鿿" for ch in value):
        return False
    markers = ("：", "成本", "下降", "上升", "需要", "必须", "开始", "成为", "进入", "风险", "可以")
    return any(marker in value for marker in markers)


def _looks_like_repo_slug(value: str) -> bool:
    if "/" not in value or any("一" <= ch <= "鿿" for ch in value):
        return False
    owner, repo = value.split("/", 1)
    return bool(owner.strip() and repo.strip())


def _mostly_english(value: str) -> bool:
    letters = sum(1 for ch in value if "a" <= ch.lower() <= "z")
    return letters > max(6, len(value) // 4)


def enrich(opportunity: dict) -> dict:
    """为成功与降级路径都补齐稳定字段，避免展示层猜结构。"""
    theme = str(opportunity.get("discovery_theme") or "")
    if not isinstance(opportunity.get("is_ai_application"), bool):
        opportunity["is_ai_application"] = infer_ai_relevance(opportunity)
    category = str(opportunity.get("category") or "").strip()
    if category not in CATEGORIES:
        is_ai = opportunity.get("is_ai_application") is True
        kind = str(opportunity.get("opportunity_type") or "")
        if is_ai:
            category = "Agent" if "Agent" in theme else (
                "AI × 工业" if "工业" in theme else "AI应用"
            )
        elif "实体" in kind or any(word in theme for word in ("消费品", "零售", "制造")):
            category = "实体产品"
        elif "内容" in kind or "内容" in theme:
            category = "虚拟内容"
        else:
            category = "服务"
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
    opportunity["business_stage"] = business_stage(opportunity)

    fallback_tags = [
        *(opportunity.get("source_tags") or []),
        category,
        industry if industry != "跨行业" else "",
        opportunity.get("opportunity_type") or "",
    ]
    tags = normalize_tags(opportunity.get("tags"), fallback_tags)
    opportunity["tags"] = tags or [category]

    if failed_judgement or _needs_title_rewrite(str(opportunity.get("idea") or ""), opportunity):
        opportunity["idea"] = _plain_chinese_title(opportunity, category, industry)
    if failed_judgement:
        opportunity.setdefault("hook", opportunity["idea"])
        opportunity.setdefault("pain", "原始材料只证明它是一个可研究的成果或信号，尚未证明具体用户痛点。")
        opportunity.setdefault("buyer", "待验证：需要找到真正有预算并愿意签字的目标用户。")
        opportunity.setdefault("money", "待验证：先用预售、付费试点或小额订阅验证真实支付意愿。")
        opportunity.setdefault("angle", "先从最窄的高频任务切入，验证一次交付能否省时间或提升质量。")
        opportunity.setdefault("risk", "最大风险是只有技术热度，没有持续付费或复购证据。")
    return opportunity
