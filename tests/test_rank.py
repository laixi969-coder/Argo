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


def test_rank_hides_scores_below_30():
    opps = [
        {"verdict": "待验证", "score": 29, "title": "low", "idea": "低分机会"},
        {"verdict": "待验证", "score": 30, "title": "edge", "idea": "门槛机会"},
    ]

    assert [o["title"] for o in rank(opps)] == ["edge"]


def test_rank_reserves_seats_for_existing_products():
    demand = [
        {"verdict": "真需求", "score": 100 - i, "title": f"d{i}", "idea": f"需求{i}"}
        for i in range(20)
    ]
    products = [
        {"verdict": "待验证", "score": 60 - i, "title": f"p{i}", "idea": f"产品{i}",
         "opportunity_type": "已有成果产品"}
        for i in range(8)
    ]

    out = rank(demand + products, n=20, min_product_pool=6)

    assert len(out) == 20
    assert sum(o.get("opportunity_type") == "已有成果产品" for o in out) == 6


def test_rank_outcome_reservation_also_covers_agents_and_demos():
    demand = [
        {"verdict": "真需求", "score": 100 - i, "idea": f"需求{i}"}
        for i in range(20)
    ]
    outcomes = [
        {"verdict": "待验证", "score": 50 - i, "idea": f"成果{i}",
         "opportunity_type": "Agent 成果", "is_outcome": True}
        for i in range(6)
    ]

    out = rank(demand + outcomes, n=20, min_product_pool=6)

    assert sum(o.get("is_outcome") is True for o in out) == 6


def test_rank_reserves_distinct_industries_above_threshold():
    general = [
        {"verdict": "真需求", "score": 100 - i, "idea": f"通用{i}", "industry": "跨行业"}
        for i in range(20)
    ]
    industries = [
        {"verdict": "真需求", "score": 50 - i, "idea": industry, "industry": industry}
        for i, industry in enumerate(["制造业", "医疗健康", "教育", "金融", "农业"])
    ]

    out = rank(general + industries, n=20, min_product_pool=0, min_industry_pool=5)

    assert {o["industry"] for o in out if o["industry"] != "跨行业"} == {
        "制造业", "医疗健康", "教育", "金融", "农业",
    }
