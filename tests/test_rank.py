from src.rank import rank

def test_rank_drops_fake_demand_and_sorts():
    opps = [
        {"verdict": "真需求", "score": 80, "title": "a", "idea": "机会A"},
        {"verdict": "伪需求", "score": 99, "title": "b", "idea": "机会B"},
        {"verdict": "待验证", "score": 60, "title": "c", "idea": "机会C"},
    ]
    out = rank(opps, n=20)
    titles = [o["title"] for o in out]
    assert "b" not in titles
    assert titles == ["a", "c"]


def test_rank_drops_unknown_idea_noise():
    opps = [
        {"verdict": "真需求", "score": 80, "title": "a", "idea": "机会A"},
        {"verdict": "待验证", "score": 95, "title": "news", "idea": "未知"},
        {"verdict": "待验证", "score": 90, "title": "empty", "idea": ""},
    ]
    out = rank(opps, n=20)
    assert [o["title"] for o in out] == ["a"]
