"""痛点/抱怨词库：用于搜 Reddit 评论区，挖"骂出来的痛"（与 demand_keywords 的"明说想要"互补）。

评论搜索精度一般（松散匹配），靠下游 extract + /req 打分过滤噪音。这里选偏
"产品缺口 / 手动痛点"的句式，尽量低噪。
"""

KEYWORDS = [
    "there should be an app",
    "wish there was an app to",
    "someone needs to make",
    "why isn't there an app",
    "hate that I have to",
    "tired of having to",
    "is there really no",
]
