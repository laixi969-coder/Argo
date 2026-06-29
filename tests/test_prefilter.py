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
