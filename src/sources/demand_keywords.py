"""需求信号词库：跨平台(TikTok / Reddit / 未来 Twitter、YouTube)共用。

捕捉「有人在痛 + 有人愿掏钱」的自然表达。赛道不限，靠这些"句式"过滤出
真实需求线索，再交给下游 /req 真需求框架精判。
"""

# 痛点 + 求解 + 付费意愿三类句式
KEYWORDS = [
    # 求解 / 缺口
    "I wish there was an app",
    "is there an app that",
    "why is there no app for",
    "does an app exist for",
    "what app do you wish existed",
    "looking for a tool that",
    "wish there was a tool",
    "need a service that",
    # 号召有人来做
    "someone should make",
    "someone should build",
    # 付费意愿
    "I would pay for",
    "I'd pay for",
    "shut up and take my money",
    "willing to pay for",
    # 手动痛点
    "tired of doing this manually",
]
