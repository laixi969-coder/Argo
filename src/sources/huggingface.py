"""Hugging Face Spaces 成果源：抓可直接运行的热门 AI Demo。"""

import requests
from src.taxonomy import infer_industry

URL = "https://huggingface.co/api/spaces"
_COUNT = 40


def _theme(text: str, tags: list[str]) -> str:
    haystack = f"{text} {' '.join(tags)}".lower()
    if any(k in haystack for k in (
        "industrial", "manufactur", "factory", "predictive maintenance",
        "quality inspection", "anomaly detection",
    )):
        return "AI × 工业"
    if any(k in haystack for k in ("agent", "mcp-server", "tool-use", "computer-use")):
        return "Agent"
    return "AI Demo"


def fetch() -> list[dict]:
    params = [
        ("sort", "trendingScore"), ("direction", "-1"), ("limit", _COUNT),
        ("expand", "cardData"), ("expand", "likes"),
        ("expand", "trendingScore"), ("expand", "createdAt"),
        ("expand", "lastModified"), ("expand", "tags"), ("expand", "sdk"),
    ]
    response = requests.get(URL, params=params, headers={"User-Agent": "argo/0.1"}, timeout=30)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, list):
        raise RuntimeError(f"Hugging Face 返回异常: {str(body)[:200]}")

    out = []
    for item in body:
        space_id = str(item.get("id") or "").strip()
        if not space_id or item.get("private"):
            continue
        card = item.get("cardData") if isinstance(item.get("cardData"), dict) else {}
        title = str(card.get("title") or space_id.rsplit("/", 1)[-1]).strip()
        description = str(card.get("short_description") or "").strip()
        tags = [str(tag) for tag in (item.get("tags") or [])]
        theme = _theme(f"{title} {description}", tags)
        industry = infer_industry(f"{title} {description} {' '.join(tags)}")
        likes = int(item.get("likes") or 0)
        trending = float(item.get("trendingScore") or 0)
        out.append({
            "source": "huggingface",
            "title": title,
            "raw_text": (
                f"{description}\n可运行 Space；{likes} likes；"
                f"SDK: {item.get('sdk') or '未知'}；标签: {', '.join(tags)}"
            ).strip(),
            "url": f"https://huggingface.co/spaces/{space_id}",
            "signal": float(min(max(trending, likes / 10), 100)),
            "opportunity_type": "Agent 成果" if theme == "Agent" else "可运行 Demo",
            "is_outcome": True,
            "discovery_theme": theme,
            "category": theme if theme in {"Agent", "AI × 工业"} else "AI应用",
            "industry_hint": industry,
            "source_tags": tags,
            "published_at": item.get("createdAt") or item.get("lastModified") or "",
        })
    return out
