"""AI 行业应用雷达：用 Hacker News 公开 API 定向扫描各行业落地信号。"""

from datetime import timedelta

import requests

from src import clock

URL = "https://hn.algolia.com/api/v1/search_by_date"
_PER_INDUSTRY = 10
QUERIES = {
    "制造业": "AI manufacturing quality inspection",
    "医疗健康": "AI healthcare workflow",
    "教育": "AI education teacher",
    "金融": "AI finance operations",
    "零售电商": "AI retail inventory",
    "法律合规": "AI legal contract",
    "人力资源": "AI recruiting HR",
    "农业": "AI agriculture farm",
    "物流供应链": "AI logistics supply chain",
    "房地产建筑": "AI construction",
}


def _search(query: str) -> list[dict]:
    since = int((clock.now() - timedelta(days=180)).timestamp())
    response = requests.get(
        URL,
        params={
            "query": query,
            "tags": "story",
            "hitsPerPage": _PER_INDUSTRY,
            "numericFilters": f"created_at_i>{since}",
        },
        headers={"User-Agent": "argo/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("hits"), list):
        raise RuntimeError(f"行业应用源返回异常: {str(body)[:200]}")
    return body["hits"]


def fetch() -> list[dict]:
    out, seen, errors = [], set(), []
    for industry, query in QUERIES.items():
        try:
            hits = _search(query)
        except Exception as exc:
            errors.append(f"{industry}: {exc}")
            continue
        for hit in hits:
            title = str(hit.get("title") or "").strip()
            if not title:
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if not url or url in seen:
                continue
            seen.add(url)
            is_product = title.lower().startswith("show hn:")
            out.append({
                "source": "industry_cases",
                "title": title,
                "raw_text": hit.get("story_text") or "",
                "url": url,
                "signal": float(min(hit.get("points", 0) or 0, 100)),
                "opportunity_type": "已有成果产品" if is_product else "行业应用信号",
                "is_outcome": is_product,
                "discovery_theme": f"AI 行业应用 · {industry}",
                "industry_hint": industry,
                "category": "AI × 工业" if industry == "制造业" else "AI应用",
                "source_tags": [industry, "行业应用"],
                "published_at": hit.get("created_at") or "",
            })
    if not out and errors:
        raise RuntimeError("；".join(errors))
    return out
