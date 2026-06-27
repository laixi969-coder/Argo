"""Argo 大脑：渠道无关。

任何接口（Telegram / 网页 / 对外 API / 飞书…）都只调 handle_message，
不在这里出现任何 Telegram 概念。换工具 = 再写一个适配器接这里，核心不动。

商业化升级路径：user_id 已贯穿全链路。要做多用户时，把 report/config/seen/日志
按 user_id 隔离（每人一个 data/<user_id>/ 目录）即可，handle_message 的契约不变。
"""
import json
from datetime import datetime
from pathlib import Path
from src import llm, bot_admin as admin

DATA = Path(__file__).resolve().parent.parent / "data"
REPORT = DATA / "latest_report.json"
CHAT_LOG = DATA / "chat_log.jsonl"

SYSTEM = """你是「金羊毛 Argo」，产品机会雷达助手。用户是想靠产品机会赚钱的操盘手 / 创业者。
你的任务：陪用户探讨机会——哪条值得做、为什么有人愿掏钱、怎么变现、怎么切入、风险在哪。
原则：通过判定痛点是否真实存在、机会是否有价值、是否有真实的付费人群、变现路径是否清晰合理来戳破伪机会，给真实判断不谄媚，结论先行再给理由，中文回答。
下面是今天的机会榜单，用户说「第 N 条」就是指这里的序号。"""

_sessions: dict[str, list] = {}  # user_id -> 最近几轮对话（内存，重启清空；日志仍落盘）


def load_report() -> str:
    if not REPORT.exists():
        return "（今天还没有榜单，可能流水线还没跑。）"
    opps = json.loads(REPORT.read_text())
    return "\n".join(
        f"{i + 1}. {o['idea']} | {o['verdict']} {int(o['score'])}分 | {o['reason']} | {o['url']}"
        for i, o in enumerate(opps)
    ) or "（今天无机会入榜。）"


def log_turn(user_id: str, role: str, text: str) -> None:
    DATA.mkdir(exist_ok=True)
    with CHAT_LOG.open("a") as f:
        f.write(json.dumps({"t": datetime.now().isoformat(), "user": user_id,
                            "role": role, "text": text}, ensure_ascii=False) + "\n")


def discuss(user_id: str, user_text: str) -> str:
    history = _sessions.setdefault(user_id, [])
    history.append({"role": "user", "content": user_text})
    del history[:-12]  # 只留最近 6 轮，控制 token
    messages = [
        {"role": "system", "content": f"{SYSTEM}\n\n今日榜单：\n{load_report()}"},
        *history,
    ]
    answer = llm.chat_llm(messages)
    history.append({"role": "assistant", "content": answer})
    del history[:-12]
    return answer


def handle_message(text: str, user_id: str = "me") -> str:
    """渠道无关的统一入口：命令走后台，其余走机会探讨。出错不抛，返回人话。"""
    log_turn(user_id, "user", text)
    try:
        reply = admin.handle(text) if admin.is_command(text) else discuss(user_id, text)
    except Exception as e:
        reply = f"（出错了：{e}）"
    log_turn(user_id, "assistant", reply)
    return reply
