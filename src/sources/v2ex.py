from datetime import datetime, timezone

import requests

# V2EX 公开 API：无需 key，永久免费。中文互联网里少有的高质量创造者社区。
# 按节点抓而非全站热榜——热榜是新闻，节点里才有「谁在痛、谁掏钱、谁做出来了」。
URL = "https://www.v2ex.com/api/topics/show.json"
_HEADERS = {"User-Agent": "argo/0.1"}

# 节点 → (机会类型, 是否成果)
# outsourcing=外包节点，帖子自带预算与付费意愿；ideas=奇思妙想，原始需求表达；
# create=分享创造，中文圈的 Show HN，已做出来的成果产品。
NODES = {
    "outsourcing": ("需求信号", False),
    "ideas": ("需求信号", False),
    "create": ("已有成果产品", True),
}


def _topics(node):
    r = requests.get(URL, params={"node_name": node}, headers=_HEADERS, timeout=30)
    r.raise_for_status()
    body = r.json()
    if not isinstance(body, list):
        raise RuntimeError(f"V2EX 返回异常: {str(body)[:200]}")
    return body


def fetch():
    out, seen = [], set()
    for node, (opportunity_type, is_outcome) in NODES.items():
        try:
            topics = _topics(node)
        except Exception as exc:  # 单节点失败不拖垮整源
            print(f"[v2ex] 节点 {node} 失败: {exc}")
            continue
        for t in topics:
            title = t.get("title")
            url = t.get("url") or ""
            if not title or not url or url in seen:
                continue
            seen.add(url)
            replies = int(t.get("replies") or 0)
            # 外包帖回复少但本身就是付费需求，给基础信号分兜底
            signal = float(min(replies * 4 + (30 if node == "outsourcing" else 0), 100))
            created = t.get("created")
            published = (
                datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                if created else ""
            )
            out.append({
                "source": "v2ex",
                "title": title,
                "raw_text": t.get("content") or "",
                "url": url,
                "signal": signal,
                "opportunity_type": opportunity_type,
                "is_outcome": is_outcome,
                "published_at": published,
            })
    return out
