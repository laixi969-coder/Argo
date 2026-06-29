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
    print(f"[漏斗] 抓取合计 {len(opps)}")
    top = prefilter.prefilter(opps, n=60)
    print(f"[漏斗] 源公平粗筛 → {len(top)}")
    top = dedup.filter_fresh(top, min_keep=15)
    print(f"[漏斗] 去重保鲜 → {len(top)}")
    top = extract.extract_ideas(top)
    # 剔除新闻/段子/公告等非需求内容，再进昂贵的真需求精判（去噪 + 省 LLM 调用）
    top = [o for o in top if o.get("is_demand", True)]
    print(f"[漏斗] 剔除非需求(is_demand) → {len(top)}")
    top = score.score_real_demand(top)
    final = rank.rank(top, n=20)
    print(f"[漏斗] 精判+排序(去伪需求/未知) → {len(final)}")
    _save(final)
    store.append(final)
    dedup.mark_seen(final)  # 结果已存妥即登记去重，不受发送成败影响
    try:
        _deliver(final, missing)
    except Exception as exc:  # 发送失败不算流水线失败：结果已存网站，下次再推
        print(f"[warn] 发送失败（结果已存网站）: {exc}")
    print(f"[ok] 保存 {len(final)} 条机会，缺源 {missing}")


if __name__ == "__main__":
    run()
