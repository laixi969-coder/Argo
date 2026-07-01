import requests
from src import config

QUERY = """{ posts(order: VOTES, first: 50) { edges { node {
  name tagline description votesCount url } } } }"""

def fetch():
    if not config.get("PRODUCTHUNT_TOKEN"):
        raise RuntimeError("Product Hunt token 未配置")
    r = requests.post("https://api.producthunt.com/v2/api/graphql",
        headers={"Authorization": f"Bearer {config.get('PRODUCTHUNT_TOKEN')}",
                 "Content-Type": "application/json"},
        json={"query": QUERY}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"PH API 报错: {body['errors']}")
    if "data" not in body or not body["data"].get("posts"):
        raise RuntimeError(f"PH 返回异常(token 或限流?): {str(body)[:200]}")
    out = []
    for e in body["data"]["posts"]["edges"]:
        n = e["node"]
        out.append({
            "source": "producthunt", "title": n["name"],
            "raw_text": f"{n['tagline']}\n{n.get('description','')}",
            "url": n["url"], "signal": float(min(n["votesCount"], 100)),
            # Product Hunt 在 Argo 中是成果产品池，不要求必须是今天发布。
            "opportunity_type": "已有成果产品",
            "is_outcome": True,
        })
    return out
