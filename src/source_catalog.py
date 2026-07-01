"""长期信息源目录；网页说明与流水线注册必须保持一致。"""

SOURCES = {
    "reddit": ("Reddit 交易社区", "真实求购、预算与付费任务", "需 Key"),
    "reddit_tikhub": ("Reddit 需求搜索", "重复痛点、绕路方案、求工具", "需 TikHub"),
    "reddit_comments_tikhub": ("Reddit 评论痛点", "评论区抱怨与隐性需求", "需 TikHub"),
    "producthunt": ("Product Hunt", "已发布产品与首批市场反馈", "需 Key"),
    "hackernews": ("Hacker News", "Show HN、需求讨论与成果产品", "公开"),
    "huggingface": ("Hugging Face Spaces", "可运行 Demo、Agent 与 MCP", "公开"),
    "github": ("GitHub", "Agent、MCP 与工业 AI 开源成果", "公开"),
    "futurepedia": ("Futurepedia", "长期 AI 产品目录与业务工具", "公开"),
    "industry_cases": ("AI 行业应用专线", "制造、医疗、教育、金融等落地案例", "公开"),
    "tikhub": ("TikTok", "产品使用场景、行为痛点与趋势信号", "需 TikHub"),
}

SCHEDULE = ("07:00", "13:00", "19:00")
