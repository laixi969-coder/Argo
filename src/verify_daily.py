"""生产流水线收尾校验：今日快照必须存在、结构完整、且不是 demo 数据。"""
from __future__ import annotations

from urllib.parse import urlsplit

from src import clock, config, store  # noqa: F401  加载本机 .env，确保校验与流水线使用同一存储


def verify(day: str | None = None) -> int:
    day = day or clock.today_iso()
    opps = store.load_day(day, include_demo=True)
    if opps is None:
        raise RuntimeError(f"今日历史缺失：history:{day}")
    for i, o in enumerate(opps, 1):
        if o.get("date") != day or not o.get("id") or not o.get("idea"):
            raise RuntimeError(f"今日历史第 {i} 条结构不完整")
        if store.is_demo_item(o):
            raise RuntimeError(f"今日历史第 {i} 条疑似 demo 数据，拒绝发布")
        try:
            score = float(o.get("score"))
        except (TypeError, ValueError):
            raise RuntimeError(f"今日历史第 {i} 条分数无效")
        if not 0 <= score <= 100:
            raise RuntimeError(f"今日历史第 {i} 条分数越界")
        url = urlsplit(o.get("url") or "")
        if url.scheme not in {"http", "https"} or not url.netloc:
            raise RuntimeError(f"今日历史第 {i} 条来源 URL 无效")
        if not o.get("category") or not o.get("industry"):
            raise RuntimeError(f"今日历史第 {i} 条分类或行业缺失")
        if o.get("commercial_potential") not in {"高", "中", "低"}:
            raise RuntimeError(f"今日历史第 {i} 条商业潜力标签无效")
        if not isinstance(o.get("tags"), list) or not o["tags"]:
            raise RuntimeError(f"今日历史第 {i} 条标签缺失")
        if o.get("is_ai_application") is not True:
            raise RuntimeError(f"今日历史第 {i} 条不是 AI 应用")
    print(f"[ok] 今日历史校验通过：{day}，累计 {len(opps)} 条")
    return len(opps)


if __name__ == "__main__":
    verify()
