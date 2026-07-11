"""长期信息源目录；网页说明与流水线注册必须保持一致。"""

SOURCES = {
    "reddit": ("Reddit 需求社区", "真实求购、预算、重复任务与付费任务", "需 Key"),
    "reddit_tikhub": ("Reddit 需求搜索", "重复痛点、绕路方案、求工具或服务", "需 TikHub"),
    "reddit_comments_tikhub": ("Reddit 评论痛点", "评论区抱怨与隐性需求", "需 TikHub"),
    "producthunt": ("Product Hunt", "已发布产品、定价线索与首批市场反馈", "需 Key"),
    "hackernews": ("Hacker News", "需求讨论、Show HN 与可验证的创业信号", "公开"),
    "huggingface": ("Hugging Face Spaces", "可运行 AI Demo、Agent 与交付能力", "公开"),
    "github": ("GitHub", "开源成果、开发者工作流与技术供给变化", "公开"),
    "futurepedia": ("Futurepedia", "长期工具目录与已有商业解法", "公开"),
    "industry_cases": ("行业应用专线", "制造、医疗、教育、金融等可量化损失案例", "公开"),
    "tikhub": ("TikTok", "消费场景、行为痛点与需求表达", "需 TikHub"),
    "v2ex": ("V2EX", "外包付费需求、奇思妙想与中文圈成果产品", "公开"),
    "eleduck": ("电鸭社区", "独立产品发布、远程雇佣需求与出海一线信号", "公开"),
}

SCHEDULE = ("07:00", "13:00", "19:00")
