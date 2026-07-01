"""GitHub 官方搜索 API 成果源：Agent、MCP 与工业 AI 开源项目。"""

from datetime import timedelta

import requests

from src import clock
from src.taxonomy import infer_industry

URL = "https://api.github.com/search/repositories"
_PER_QUERY = 15
_QUERIES = (
    ("Agent", "topic:ai-agent stars:>50"),
    ("Agent", "topic:mcp stars:>20"),
    ("AI × 工业", '"industrial ai" stars:>10'),
    ("AI × 工业", '"predictive maintenance" machine-learning stars:>10'),
    ("AI × 工业", '"quality inspection" computer-vision stars:>10'),
)


def _search(query: str) -> list[dict]:
    since = (clock.now().date() - timedelta(days=30)).isoformat()
    response = requests.get(
        URL,
        params={
            "q": f"{query} pushed:>={since}",
            "sort": "updated", "order": "desc", "per_page": _PER_QUERY,
        },
        headers={"Accept": "application/vnd.github+json", "User-Agent": "argo/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise RuntimeError(f"GitHub 返回异常: {str(body)[:200]}")
    return body["items"]


def fetch() -> list[dict]:
    out, seen = [], set()
    errors = []
    for theme, query in _QUERIES:
        try:
            repos = _search(query)
        except Exception as exc:
            errors.append(f"{theme}: {exc}")
            continue
        for repo in repos:
            url = str(repo.get("html_url") or "").strip()
            if not url or url in seen or repo.get("archived"):
                continue
            seen.add(url)
            name = str(repo.get("full_name") or repo.get("name") or "").strip()
            description = str(repo.get("description") or "").strip()
            topics = [str(topic) for topic in (repo.get("topics") or [])]
            industry = infer_industry(f"{name} {description} {' '.join(topics)}")
            stars = int(repo.get("stargazers_count") or 0)
            forks = int(repo.get("forks_count") or 0)
            out.append({
                "source": "github",
                "title": name,
                "raw_text": (
                    f"{description}\n开源项目；{stars} stars；{forks} forks；"
                    f"主题: {', '.join(topics)}"
                ).strip(),
                "url": url,
                "signal": float(min(max(stars / 10, forks / 3), 100)),
                "opportunity_type": "工业 AI 成果" if theme == "AI × 工业" else "Agent 成果",
                "is_outcome": True,
                "discovery_theme": theme,
                "category": theme,
                "industry_hint": "制造业" if theme == "AI × 工业" else industry,
                "source_tags": topics,
                "published_at": repo.get("created_at") or "",
            })
    if not out and errors:
        raise RuntimeError("；".join(errors))
    return out
