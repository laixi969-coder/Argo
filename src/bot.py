"""Telegram 适配器：只管 Telegram 收发，业务逻辑全在 src.agent。

换工具（飞书/网页/对外 API）= 照这个样子再写一个适配器调 agent.handle_message，
core 不动。本进程常驻 Mac mini，launchd KeepAlive 保活。
"""
import time
from src import config, telegram, agent


def run() -> None:
    if not config.get("TELEGRAM_BOT_TOKEN"):
        raise SystemExit("[stop] TELEGRAM_BOT_TOKEN 未配置，先填 .env 再启动 bot")
    if not config.get("LLM_API_KEY"):
        print("[warn] LLM_API_KEY 未配置，能收消息但答不了，请先填 .env")
    me = config.get("TELEGRAM_CHAT_ID")  # Telegram 这层的鉴权：只认本人
    offset = None
    print("[ok] Argo bot 启动，等待消息…")
    while True:
        try:
            updates = telegram.get_updates(offset=offset, timeout=30)
        except Exception as e:
            print(f"[warn] 拉消息失败，5s 后重试: {e}")
            time.sleep(5)
            continue
        for up in updates:
            offset = up["update_id"] + 1
            msg = up.get("message") or {}
            text = msg.get("text")
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if not text or (me and chat_id != str(me)):
                continue  # 忽略非文本 / 非本人
            reply = agent.handle_message(text, user_id=chat_id)
            telegram.send_message(reply, chat_id=chat_id, parse_mode=None)


if __name__ == "__main__":
    run()
