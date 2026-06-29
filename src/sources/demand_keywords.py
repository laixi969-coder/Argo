"""需求信号词库：跨平台（TikTok / Reddit / HackerNews）共用，挖"明说想要/愿付钱"的帖子。

13 个按信号强度分档的完整需求短语（付费意愿 > 召唤建造 > 求解缺口 > 痛点 > AI 专项）。
刻意放宽 app→tool/service 以覆盖实体/服务/AI 机会。评论区"抱怨型痛点"另见 pain_keywords.py。
"""

KEYWORDS = [
    # 付费意愿（最强信号）
    "I would pay for",
    "shut up and take my money",
    "I'd happily pay for",
    "take my money",
    # 召唤有人来做
    "someone should make",
    "why is there no",
    "why hasn't anyone built",
    # 求解 / 缺口（去 app 偏向）
    "looking for a tool that",
    "is there a tool that",
    "I wish there was a tool",
    # 痛点 → 机会
    "tired of doing this manually",
    "wasting hours on",
    # AI 专项
    "is there an AI that",
]
