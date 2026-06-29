"""联通烟雾测试：填完 key 后跑一次，逐项真实 ping，看每个 key 到底通不通。

跑：python3 -m src.smoke
和 doctor 的区别：doctor 查 key 填没填；smoke 查 key 能不能用（真发请求）。
会真打网络、真发一条 Telegram 测试消息给你。
"""
from src import config, telegram, llm
from src.sources import reddit, producthunt, hackernews


def _check(name: str, fn) -> bool:
    try:
        msg = fn()
        print(f"✅ {name}：{msg}")
        return True
    except Exception as e:
        print(f"❌ {name}：{type(e).__name__}: {e}")
        return False


def _llm():
    out = llm.call_llm("只回复两个字：在线", timeout=30)
    return f"模型回话「{out.strip()[:20]}」"


def _telegram():
    me = telegram.get_me()
    telegram.send_message("🛰️ Argo 联通测试：收到这条就说明推送通了。", parse_mode=None)
    return f"机器人 @{me.get('username')}，测试消息已发给你"


def _ph():
    n = len(producthunt.fetch())
    return f"抓到 {n} 条"


def _hn():
    return f"抓到 {len(hackernews.fetch())} 条"


def _reddit():
    if not config.get("REDDIT_CLIENT_ID"):
        return "未配置，跳过（可选源）"
    return f"抓到 {len(reddit.fetch(limit=5))} 条"


def run() -> bool:
    print("=" * 56)
    print("Argo 联通烟雾测试（真实 ping，会发一条 Telegram 消息）")
    print("=" * 56)
    results = [
        _check("大模型 LLM", _llm),
        _check("Telegram", _telegram),
        _check("Product Hunt", _ph),
        _check("Hacker News", _hn),
        _check("Reddit(可选)", _reddit),
    ]
    print("-" * 56)
    # Reddit 可选，不计入硬性通过；前四项必须全绿（HN 无需 key，恒应通）
    core_ok = all(results[:4])
    print("✅ 核心项全通，可以发车正式跑 python3 -m src.main"
          if core_ok else "❌ 还有核心项不通，按上面报错修对应 key / 网络")
    return core_ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
