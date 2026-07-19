from src.rank import rank


QUOTE = "用户每周都在手工完成这项任务"


def _with_quotes(opportunities):
    return [dict(opportunity, evidence_quotes=[QUOTE]) for opportunity in opportunities]

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
    demand = _with_quotes([
        {"verdict": "真需求", "score": 100 - i, "title": f"d{i}", "idea": f"需求{i}"}
        for i in range(20)
    ])
    products = _with_quotes([
        {"verdict": "待验证", "score": 60 - i, "title": f"p{i}", "idea": f"产品{i}",
         "opportunity_type": "已有成果产品"}
        for i in range(8)
    ])

    out = rank(demand + products, n=20, min_product_pool=6)

    assert len(out) == 20
    assert sum(o.get("opportunity_type") == "已有成果产品" for o in out) == 6


def test_rank_outcome_reservation_also_covers_agents_and_demos():
    demand = _with_quotes([
        {"verdict": "真需求", "score": 100 - i, "idea": f"需求{i}"}
        for i in range(20)
    ])
    outcomes = _with_quotes([
        {"verdict": "待验证", "score": 50 - i, "idea": f"成果{i}",
         "opportunity_type": "Agent 成果", "is_outcome": True}
        for i in range(6)
    ])

    out = rank(demand + outcomes, n=20, min_product_pool=6)

    assert sum(o.get("is_outcome") is True for o in out) == 6


def test_rank_reserves_distinct_industries_above_threshold():
    general = _with_quotes([
        {"verdict": "真需求", "score": 100 - i, "idea": f"通用{i}", "industry": "跨行业"}
        for i in range(20)
    ])
    industries = _with_quotes([
        {"verdict": "真需求", "score": 50 - i, "idea": industry, "industry": industry}
        for i, industry in enumerate(["制造业", "医疗健康", "教育", "金融", "农业"])
    ])

    out = rank(general + industries, n=20, min_product_pool=0, min_industry_pool=5)

    assert {o["industry"] for o in out if o["industry"] != "跨行业"} == {
        "制造业", "医疗健康", "教育", "金融", "农业",
    }


def test_rank_limits_unverified_ai_to_main_quota_and_keeps_remainder_in_side_track():
    ai = [
        {"verdict": "待验证", "score": 100 - i, "idea": f"AI{i}",
         "is_ai_application": True, "evidence_quotes": [QUOTE]}
        for i in range(10)
    ]

    out = rank(ai, n=10, min_product_pool=0, min_industry_pool=0)

    assert len(out) == 10
    assert sum(o["radar_track"] == "真实需求主榜" for o in out) == 4
    assert sum(o["radar_track"] == "AI 供给副榜" for o in out) == 6


def test_rank_allows_ai_with_paid_market_proof_to_break_main_quota():
    verified = [
        {"verdict": "市场已验证", "score": 90 - i, "idea": f"已付费AI{i}",
         "is_ai_application": True, "market_proof": "已有 20 位客户持续付费",
         "market_proof_verified": True,
         "evidence_quotes": ["已有 20 位客户持续付费"]}
        for i in range(5)
    ]

    out = rank(verified, n=5, min_product_pool=0, min_industry_pool=0)

    assert all(o["radar_track"] == "真实需求主榜" for o in out)


def test_rank_uses_actual_daily_count_for_ai_quota_when_report_is_short():
    ai = [
        {"verdict": "待验证", "score": 90 - i, "idea": f"AI{i}",
         "is_ai_application": True, "evidence_quotes": [QUOTE]}
        for i in range(10)
    ]

    out = rank(ai, n=20, min_product_pool=0, min_industry_pool=0)

    assert sum(o["radar_track"] == "真实需求主榜" for o in out) == 4


def test_rank_sends_candidates_without_verifiable_quote_to_evidence_side_track():
    out = rank([{"verdict": "真需求", "score": 80, "idea": "实体服务", "is_ai_application": False}], n=1)

    assert out[0]["radar_track"] == "待核验证据副榜"
