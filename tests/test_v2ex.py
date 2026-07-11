from src.sources import v2ex


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _patch(monkeypatch, payload_by_node):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _Resp(payload_by_node.get(params["node_name"], []))
    monkeypatch.setattr(v2ex.requests, "get", fake_get)


def test_fetch_parses_topics(monkeypatch):
    _patch(monkeypatch, {"ideas": [
        {"title": "想要一个自动记账工具", "content": "手动记账太烦",
         "url": "https://www.v2ex.com/t/1", "replies": 10, "created": 1783678568},
    ]})
    out = v2ex.fetch()
    assert len(out) == 1
    o = out[0]
    assert o["source"] == "v2ex" and o["opportunity_type"] == "需求信号"
    assert o["signal"] == 40.0 and o["is_outcome"] is False
    assert o["published_at"].startswith("2026-")


def test_outsourcing_gets_base_signal_and_create_is_outcome(monkeypatch):
    _patch(monkeypatch, {
        "outsourcing": [{"title": "找人做小程序，预算 2 万",
                         "url": "https://www.v2ex.com/t/2", "replies": 0}],
        "create": [{"title": "做了个导出工具",
                    "url": "https://www.v2ex.com/t/3", "replies": 50}],
    })
    out = {o["url"]: o for o in v2ex.fetch()}
    assert out["https://www.v2ex.com/t/2"]["signal"] == 30.0
    outcome = out["https://www.v2ex.com/t/3"]
    assert outcome["is_outcome"] is True and outcome["opportunity_type"] == "已有成果产品"


def test_fetch_skips_titleless_and_dedups(monkeypatch):
    _patch(monkeypatch, {"ideas": [
        {"url": "https://www.v2ex.com/t/4", "replies": 1},
        {"title": "重复", "url": "https://www.v2ex.com/t/5"},
        {"title": "重复", "url": "https://www.v2ex.com/t/5"},
    ]})
    assert len(v2ex.fetch()) == 1


def test_fetch_degrades_when_node_fails(monkeypatch):
    # 返回非列表 payload 时单节点被吞，整源降级返回空
    _patch(monkeypatch, {n: {"error": "nope"} for n in v2ex.NODES})
    assert v2ex.fetch() == []
