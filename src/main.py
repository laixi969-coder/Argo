import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.sources import hackernews, producthunt, reddit_comments_tikhub, reddit_tikhub, tikhub
from src import config, dedup, email_report, extract, prefilter, rank, score, store, telegram_report


SOURCES = {
    "reddit_tikhub": reddit_tikhub.fetch,
    "reddit_comments_tikhub": reddit_comments_tikhub.fetch,
    "producthunt": producthunt.fetch,
    "hackernews": hackernews.fetch,
    "tikhub": tikhub.fetch,
}
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


def _fetch_one(item):
    """单个源抓取，返回 (源名, 结果列表, 错误)。失败不抛，交给上层统计。"""
    name, fetch = item
    try:
        return name, fetch(), None
    except Exception as exc:
        return name, [], exc


def run():
    opps, missing = [], []
    # 各源互不依赖，并行抓取；总耗时 = 最慢的源，而非各源相加
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        results = list(pool.map(_fetch_one, SOURCES.items()))
    for name, got, exc in results:
        if exc is not None:
            missing.append(name)
            print(f"[warn] 源 {name} 失败: {exc}")
        else:
            print(f"[ok] 源 {name} 抓到 {len(got)} 条")
            opps += got
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
