from src.rank import rank

def test_rank_drops_fake_demand_and_sorts():
    opps = [
        {"verdict": "真需求", "score": 80, "title": "a"},
        {"verdict": "伪需求", "score": 99, "title": "b"},
        {"verdict": "待验证", "score": 60, "title": "c"},
    ]
    out = rank(opps, n=20)
    titles = [o["title"] for o in out]
    assert "b" not in titles
    assert titles == ["a", "c"]
