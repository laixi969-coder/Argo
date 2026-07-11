from datetime import datetime, timedelta, timezone

import requests

# 电鸭社区公开 API：无需 key，免费。国内远程工作/独立开发者聚集地，
# 帖子里有真实的雇佣需求、独立产品发布和出海一线经验。
URL = "https://svc.eleduck.com/api/v1/posts"
_HEADERS = {"User-Agent": "argo/0.1"}
_MAX_AGE_DAYS = 45  # 列表里混有多年前的置顶帖，按日期剔除

# 分类 ID → (说明, 机会类型, 是否成果)
# 15=独立产品，中文圈独立开发者的成果发布；5=招聘，真金白银的付费需求；
# 10=出海，海外市场的一线需求与解法讨论。
CATEGORIES = {
    15: ("独立产品", "已有成果产品", True),
    5: ("招聘", "需求信号", False),
    10: ("出海", "需求信号", False),
}


def _posts(category):
    r = requests.get(
        URL,
        params={"category": category, "order": "published_at"},
        headers=_HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if "posts" not in body:
        raise RuntimeError(f"电鸭返回异常: {str(body)[:200]}")
    return body["posts"]


def _fresh(published_at):
    if not published_at:
        return False
    try:
        dt = datetime.fromisoformat(published_at)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - dt <= timedelta(days=_MAX_AGE_DAYS)


def fetch():
    out, seen = [], set()
    for category, (_, opportunity_type, is_outcome) in CATEGORIES.items():
        try:
            posts = _posts(category)
        except Exception as exc:  # 单分类失败不拖垮整源
            print(f"[eleduck] 分类 {category} 失败: {exc}")
            continue
        for p in posts:
            title = p.get("title")
            pid = p.get("id")
            published = p.get("published_at") or ""
            if not title or not pid or not _fresh(published):
                continue
            url = f"https://eleduck.com/posts/{pid}"
            if url in seen:
                continue
            seen.add(url)
            upvotes = int(p.get("upvotes_count") or 0)
            comments = int(p.get("comments_count") or 0)
            out.append({
                "source": "eleduck",
                "title": title,
                "raw_text": p.get("summary") or "",
                "url": url,
                "signal": float(min(upvotes * 10 + comments * 5, 100)),
                "opportunity_type": opportunity_type,
                "is_outcome": is_outcome,
                "published_at": published,
            })
    return out
