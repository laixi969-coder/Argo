"""发车预检：检查 .env 配齐没有，给出人话报告。

跑：python3 -m src.doctor
填完 key 跑一次，绿了就能发车。
"""
from src import config

# (env key, 说明, 是否必填发车)
CHECKS = [
    ("TELEGRAM_BOT_TOKEN", "Telegram 机器人 token（@BotFather）", True),
    ("TELEGRAM_CHAT_ID", "你本人的 chat id（@userinfobot）", True),
    ("LLM_API_KEY", "大模型 key（中转站 xingyuzhida）", True),
    ("PRODUCTHUNT_TOKEN", "Product Hunt token", True),
    ("REDDIT_CLIENT_ID", "Reddit 源（可选，缺了只用 PH）", False),
    ("REDDIT_CLIENT_SECRET", "Reddit 源（可选）", False),
    ("LLM_BASE_URL", "大模型地址（有默认）", False),
    ("LLM_MODEL", "大模型名（有默认）", False),
]


def missing_required() -> list[str]:
    return [k for k, _, req in CHECKS if req and not config.get(k)]


def report() -> bool:
    print("=" * 56)
    print("Argo 发车预检")
    print("=" * 56)
    for key, desc, req in CHECKS:
        ok = bool(config.get(key))
        mark = "✅" if ok else ("❌" if req else "⚪")
        tag = "必填" if req else "可选"
        print(f"{mark} [{tag}] {key:<22} {desc}")
    miss = missing_required()
    print("-" * 56)
    if not miss:
        print("✅ 必填项齐全，可以发车：")
        print("   1) python3 -m src.main   # 抓源+推日报")
        print("   2) python3 -m src.bot    # 启动探讨")
        return True
    print(f"❌ 还差 {len(miss)} 个必填：{', '.join(miss)}")
    print("   编辑 .env 填上后再跑一次 python3 -m src.doctor")
    return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if report() else 1)
