"""机会反馈捕获：验证判断层准不准的尺子，也是数据飞轮第一铲土。

/good N、/bad N 把某条机会的好坏标记追加进 data/feedback.jsonl。
将来这些反馈可反哺真需求判断（越用越准，后来者抄不走）。
"""
import json
from pathlib import Path
from src import clock, config, kv, store

DATA = Path(__file__).resolve().parent.parent / "data"
REPORT = DATA / "latest_report.json"
FEEDBACK = DATA / "feedback.jsonl"


def _report() -> list[dict]:
    if kv.enabled():
        return store.load_day(clock.today_iso()) or []
    if not REPORT.exists():
        return []
    try:
        return json.loads(REPORT.read_text())
    except Exception:
        return []


def record(idx: int, label: str, note: str = "", user_id: str = "me") -> str:
    opps = _report()
    if idx < 1 or idx > len(opps):
        return f"⚠️ 没有第 {idx} 条（今日榜单 {len(opps)} 条）"
    o = opps[idx - 1]
    DATA.mkdir(exist_ok=True)
    with FEEDBACK.open("a") as f:
        f.write(json.dumps({
            "t": clock.now().isoformat(), "user": user_id, "label": label,
            "idx": idx, "idea": o.get("idea"), "url": o.get("url"),
            "verdict": o.get("verdict"), "score": o.get("score"), "note": note,
        }, ensure_ascii=False) + "\n")
    tag = "👍 好机会" if label == "good" else "👎 不行"
    return f"{tag}已记：第 {idx} 条「{o.get('idea')}」{('｜' + note) if note else ''}"
