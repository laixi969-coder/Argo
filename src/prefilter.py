def prefilter(opps, n=30):
    return sorted(opps, key=lambda o: o.get("signal", 0), reverse=True)[:n]
