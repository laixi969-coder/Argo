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
