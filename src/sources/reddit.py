import requests
from src import config

SUBS = ["SomebodyMakeThis", "Entrepreneur", "AppIdeas"]

def _token():
    if not config.get("REDDIT_CLIENT_ID") or not config.get("REDDIT_CLIENT_SECRET"):
        raise RuntimeError("Reddit key 未配置（可选源，跳过）")
    r = requests.post("https://www.reddit.com/api/v1/access_token",
        auth=(config.get("REDDIT_CLIENT_ID"), config.get("REDDIT_CLIENT_SECRET")),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": "argo/0.1"}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if "access_token" not in body:
        raise RuntimeError(f"Reddit 拿 token 失败(key 无效?): {str(body)[:200]}")
    return body["access_token"]

def fetch(limit=50):
    tok = _token()
    headers = {"Authorization": f"bearer {tok}", "User-Agent": "argo/0.1"}
    out = []
    for sub in SUBS:
        r = requests.get(f"https://oauth.reddit.com/r/{sub}/new",
            headers=headers, params={"limit": limit}, timeout=30)
        r.raise_for_status()
        for c in r.json()["data"]["children"]:
            d = c["data"]
            out.append({
                "source": "reddit", "title": d["title"],
                "raw_text": d.get("selftext", ""),
                "url": "https://reddit.com" + d["permalink"],
                "signal": float(min(d.get("ups", 0), 100)),
            })
    return out
