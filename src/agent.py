"""Argo 大脑：渠道无关。

任何接口（Telegram / 网页 / 对外 API / 飞书…）都只调 handle_message，
不在这里出现任何 Telegram 概念。换工具 = 再写一个适配器接这里，核心不动。

商业化升级路径：user_id 已贯穿全链路。要做多用户时，把 report/config/seen/日志
按 user_id 隔离（每人一个 data/<user_id>/ 目录）即可，handle_message 的契约不变。
"""
import json
import hashlib
from pathlib import Path
from src import clock, kv, llm, store, taxonomy, bot_admin as admin
from src.visibility import visible_only

DATA = Path(__file__).resolve().parent.parent / "data"
REPORT = DATA / "latest_report.json"
CHAT_LOG = DATA / "chat_log.jsonl"

SYSTEM = """你是「金羊毛 Argo」，产品机会雷达助手。用户是想靠产品机会赚钱的操盘手 / 创业者。
你的任务：陪用户探讨机会——哪条值得做、为什么有人愿掏钱、怎么变现、怎么切入、风险在哪。
原则：通过判定痛点是否真实存在、机会是否有价值、是否有真实的付费人群、变现路径是否清晰合理来戳破伪机会，给真实判断不谄媚，结论先行再给理由，中文回答。
下面是今天的机会榜单，用户说「第 N 条」就是指这里的序号。"""

_sessions: dict[str, list] = {}  # user_id -> 最近几轮对话（内存，重启清空；日志仍落盘）


def load_report() -> str:
    # 云端与配置了 KV 的 Mac 都读中央历史；纯本地开发才回退 latest_report.json。
    opps = store.load_day(clock.today_iso()) if kv.enabled() else None
    if opps is None:
        if not REPORT.exists():
            return "（今天还没有榜单，可能流水线还没跑。）"
        opps = [taxonomy.enrich(dict(o)) for o in json.loads(REPORT.read_text())]
    opps = visible_only(opps)
    return "\n".join(
        f"{i + 1}. {o['idea']} | {o['verdict']} {int(o['score'])}分 | "
        f"{o.get('commercial_potential', '')}商业潜力 | {o.get('industry', '跨行业')} | "
        f"标签:{'、'.join(o.get('tags') or [])} | {o['reason']} | {o['url']}"
        for i, o in enumerate(opps)
    ) or "（今天无机会入榜。）"


def log_turn(user_id: str, role: str, text: str) -> None:
    entry = {"t": clock.now().isoformat(), "user": user_id,
             "role": role, "text": text}
    if kv.enabled():
        # 用户 id 哈希后分桶，避免把任意输入直接拼进 KV key；保留最近 100 轮一年。
        kv.append_json(_chat_key(user_id), entry, max_items=200, ex=365 * 24 * 60 * 60)
        return
    DATA.mkdir(exist_ok=True)
    with CHAT_LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _chat_key(user_id: str) -> str:
    digest = hashlib.sha256(str(user_id).encode()).hexdigest()[:24]
    return f"chat:{digest}"


def _recent_cloud_history(user_id: str) -> list[dict]:
    if not kv.enabled():
        return []
    entries = kv.list_json(_chat_key(user_id), -12, -1)
    return [
        {"role": e["role"], "content": e["text"]}
        for e in entries
        if e.get("role") in {"user", "assistant"} and isinstance(e.get("text"), str)
    ]


def _safe_log_turn(user_id: str, role: str, text: str) -> None:
    """日志是旁路能力，任何存储故障都不能拖垮聊天主链路。"""
    try:
        log_turn(user_id, role, text)
    except Exception:
        pass


def discuss(user_id: str, user_text: str) -> str:
    if kv.enabled():
        messages = [
            {"role": "system", "content": f"{SYSTEM}\n\n今日榜单：\n{load_report()}"},
            *_recent_cloud_history(user_id),
            {"role": "user", "content": user_text},
        ]
        return llm.chat_llm(messages)
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
    try:
        reply = admin.handle(text) if admin.is_command(text) else discuss(user_id, text)
    except Exception as e:
        print(f"[warn] 对话失败：{type(e).__name__}: {e}")
        reply = "（对话服务响应超时或暂时不可用，请稍后重试。）"
    _safe_log_turn(user_id, "user", text)
    _safe_log_turn(user_id, "assistant", reply)
    return reply
