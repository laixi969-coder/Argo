"""Telegram 内的管理命令；本机网页设置后台位于 src.admin。"""

from src import config, feedback
from src.doctor import CHECKS


LOCKED = {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}
_SECRET_HINT = ("TOKEN", "KEY", "SECRET", "PASS")
_KNOWN = {key for key, _, _ in CHECKS}


def _mask(key, value):
    if not value:
        return "（未设）"
    if any(hint in key for hint in _SECRET_HINT):
        return f"{value[:3]}…{value[-4:]}" if len(value) > 8 else "（已设）"
    return value


def is_command(text):
    return text.strip().startswith("/")


def handle(text):
    parts = text.strip().split(maxsplit=2)
    cmd = parts[0].lower()
    if cmd in ("/help", "/start"):
        return ("Argo 后台命令：\n/good N [备注] 标记好机会\n/bad N [备注] 标记不行\n"
                "/config 查看配置\n/model 名称 换模型\n/api 地址 换接口地址")
    if cmd in ("/good", "/bad"):
        if len(parts) < 2 or not parts[1].isdigit():
            return f"用法：{cmd} 3 [可选备注]"
        return feedback.record(int(parts[1]), cmd[1:], parts[2] if len(parts) > 2 else "")
    if cmd == "/config":
        lines = ["当前配置："]
        for key, _, required in CHECKS:
            lines.append(f"{'·' if required else '○'} {key} = {_mask(key, config.get(key) or '')}")
        return "\n".join(lines)
    if cmd == "/model":
        if len(parts) < 2:
            return "用法：/model deepseek-chat"
        config.set_override("LLM_MODEL", parts[1])
        return f"✅ 大模型已切到 {parts[1]}"
    if cmd == "/api":
        if len(parts) < 2:
            return "用法：/api https://api.deepseek.com"
        config.set_override("LLM_BASE_URL", parts[1])
        return f"✅ 接口地址已切到 {parts[1]}"
    if cmd == "/set":
        if len(parts) < 3:
            return "用法：/set LLM_API_KEY sk-xxxx"
        key, value = parts[1], parts[2]
        if key in LOCKED:
            return f"⚠️ {key} 不能用命令改，请在本机设置页修改"
        if key not in _KNOWN:
            return f"⚠️ 未知配置项 {key}"
        config.set_override(key, value)
        return f"✅ 已设 {key} = {_mask(key, value)}（立即生效）"
    return "未知命令，发 /help 看用法"
