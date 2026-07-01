"""Futurepedia 长期产品目录源：抓已整理的 AI 工具与 Agent 产品。"""

import json
import re
import requests

BASE = "https://www.futurepedia.io/ai-tools"
_PAGES = {
    "ai-agents": ("Agent", "跨行业"),
    "business": ("AI应用", "企业服务"),
    "finance": ("AI应用", "金融"),
    "marketing": ("AI应用", "营销广告"),
    "video": ("AI应用", "内容创意"),
}
_PER_PAGE = 20
_TOOL_RE = re.compile(
    r'\\"toolName\\":\\"(.*?)\\".*?'
    r'\\"toolShortDescription\\":\\"(.*?)\\".*?'
    r'\\"verified\\":(true|false).*?'
    r'\\"websiteUrl\\":\\"(.*?)\\"',
    re.DOTALL,
)


def _decode(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except (json.JSONDecodeError, TypeError):
        return str(value or "").replace(r"\u0026", "&").replace(r'\"', '"')


def _parse(html: str, slug: str) -> list[dict]:
    category, industry = _PAGES[slug]
    out, seen = [], set()
    for name, description, verified, website in _TOOL_RE.findall(html):
        name, description, website = map(_decode, (name, description, website))
        if not name or not website.startswith(("http://", "https://")) or website in seen:
            continue
        seen.add(website)
        out.append({
            "source": "futurepedia",
            "title": name,
            "raw_text": f"{description}\nFuturepedia verified: {verified}",
            "url": website,
            "signal": 70.0 if verified == "true" else 40.0,
            "opportunity_type": "Agent 成果" if category == "Agent" else "已有成果产品",
            "is_outcome": True,
            "discovery_theme": f"Futurepedia · {slug}",
            "industry_hint": industry,
            "category": category,
            "source_tags": [slug, "产品目录"],
        })
        if len(out) >= _PER_PAGE:
            break
    return out


def _fetch_page(slug: str) -> list[dict]:
    response = requests.get(
        f"{BASE}/{slug}", headers={"User-Agent": "Mozilla/5.0 Argo/1.0"}, timeout=30,
    )
    response.raise_for_status()
    return _parse(response.text, slug)


def fetch() -> list[dict]:
    # 该站会主动断开同 IP 的并发 TLS；串行抓取更慢一点，但长期任务更稳定。
    out, seen, errors = [], set(), []
    results = []
    for slug in _PAGES:
        try:
            results.append(_fetch_page(slug))
        except Exception as exc:
            errors.append(f"{slug}: {exc}")
    for page in results:
        for item in page:
            if item["url"] not in seen:
                seen.add(item["url"])
                out.append(item)
    if not out:
        detail = "；".join(errors) if errors else "页面结构变化或没有可用产品"
        raise RuntimeError(f"Futurepedia 无可用产品：{detail}")
    return out
