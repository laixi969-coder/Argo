from src.prefilter import prefilter

def test_prefilter_keeps_top_n_by_signal():
    opps = [{"signal": i, "title": str(i)} for i in range(50)]
    out = prefilter(opps, n=30)
    assert len(out) == 30
    assert out[0]["signal"] == 49
    assert all(out[i]["signal"] >= out[i+1]["signal"] for i in range(len(out)-1))

def test_prefilter_handles_fewer_than_n():
    opps = [{"signal": 1, "title": "a"}]
    assert len(prefilter(opps, n=30)) == 1


def test_prefilter_gives_every_source_a_seat():
    # reddit 40 条全顶满 100，其它源信号低；旧逻辑会被 reddit 霸榜
    opps = [{"signal": 100, "source": "reddit", "title": f"r{i}"} for i in range(40)]
    opps += [{"signal": 30, "source": "producthunt", "title": "ph"}]
    opps += [{"signal": 20, "source": "hackernews", "title": "hn"}]
    out = prefilter(opps, n=5)
    sources = {o["source"] for o in out}
    assert "producthunt" in sources and "hackernews" in sources


def test_prefilter_reserves_existing_product_candidates():
    demand = [
        {"signal": 100 - i, "source": "reddit", "title": f"d{i}"}
        for i in range(30)
    ]
    products = [
        {"signal": 10 - i, "source": "hackernews", "title": f"p{i}",
         "opportunity_type": "已有成果产品"}
        for i in range(8)
    ]

    out = prefilter(demand + products, n=12, min_product_pool=4)

    assert len(out) == 12
    assert sum(o.get("opportunity_type") == "已有成果产品" for o in out) >= 4


def test_prefilter_reserves_distinct_industry_candidates():
    general = [
        {"signal": 100 - i, "source": "reddit", "title": f"g{i}"}
        for i in range(30)
    ]
    industries = [
        {"signal": 10 - i, "source": "industry_cases", "title": f"i{i}",
         "industry_hint": industry}
        for i, industry in enumerate(["医疗健康", "教育", "金融", "农业", "物流供应链"])
    ]

    out = prefilter(general + industries, n=12, min_product_pool=0, min_industry_pool=5)

    assert {o.get("industry_hint") for o in out if o.get("industry_hint")} == {
        "医疗健康", "教育", "金融", "农业", "物流供应链",
    }
