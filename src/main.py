import json
import os
from pathlib import Path

from src.sources import producthunt, reddit, tikhub
from src import config, dedup, email_report, extract, prefilter, rank, score, store, telegram_report


SOURCES = {"reddit": reddit.fetch, "producthunt": producthunt.fetch, "tikhub": tikhub.fetch}
REPORT = Path(__file__).resolve().parent.parent / "data" / "latest_report.json"


def _save(opps):
    REPORT.parent.mkdir(exist_ok=True)
    temp = REPORT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(opps, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, REPORT)


def _deliver(opps, missing):
    delivered = False
    if config.get("SMTP_PASS"):
        email_report.send_report(opps, missing)
        delivered = True
    if config.get("TELEGRAM_BOT_TOKEN") and config.get("TELEGRAM_CHAT_ID"):
        telegram_report.send_report(opps, missing)
        delivered = True
    if not delivered:
        print("[warn] 未配置邮件或 Telegram，结果仅保存到本地网站")


def run():
    opps, missing = [], []
    for name, fetch in SOURCES.items():
        try:
            opps += fetch()
        except Exception as exc:
            missing.append(name)
            print(f"[warn] 源 {name} 失败: {exc}")
    if not opps:
        _save([])
        _deliver([], list(SOURCES))
        return
    top = prefilter.prefilter(opps, n=30)
    top = dedup.filter_fresh(top, min_keep=15)
    top = extract.extract_ideas(top)
    top = score.score_real_demand(top)
    final = rank.rank(top, n=20)
    _save(final)
    store.append(final)
    _deliver(final, missing)
    dedup.mark_seen(final)
    print(f"[ok] 保存并发送 {len(final)} 条机会，缺源 {missing}")


if __name__ == "__main__":
    run()
