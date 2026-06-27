def rank(opps, n=20):
    kept = [o for o in opps if o.get("verdict") != "伪需求"]
    return sorted(kept, key=lambda o: o.get("score", 0), reverse=True)[:n]
