import pytest
from src.sources import hackernews


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _patch(monkeypatch, payload):
    monkeypatch.setattr(hackernews.requests, "get", lambda *a, **k: _Resp(payload))


def test_fetch_parses_hits(monkeypatch):
    _patch(monkeypatch, {"hits": [
        {"title": "Foo", "story_text": "bar", "url": "http://x",
         "points": 30, "objectID": "1"},
    ]})
    out = hackernews.fetch()
    assert out[0]["title"] == "Foo" and out[0]["source"] == "hackernews"
    assert out[0]["signal"] == 30.0


def test_fetch_caps_signal_and_falls_back_url(monkeypatch):
    _patch(monkeypatch, {"hits": [
        {"title": "Ask HN: x", "points": 500, "objectID": "42"},
    ]})
    out = hackernews.fetch()
    assert out[0]["signal"] == 100.0
    assert out[0]["url"] == "https://news.ycombinator.com/item?id=42"


def test_fetch_skips_titleless(monkeypatch):
    _patch(monkeypatch, {"hits": [{"points": 10, "objectID": "9"}]})
    assert hackernews.fetch() == []


def test_search_raises_on_bad_payload(monkeypatch):
    _patch(monkeypatch, {"error": "nope"})
    with pytest.raises(RuntimeError, match="返回异常"):
        hackernews._search("kw")


def test_fetch_degrades_to_empty_when_all_keywords_fail(monkeypatch):
    # 坏 payload 时单关键词失败被吞，整源降级返回空，不拖垮流水线
    _patch(monkeypatch, {"error": "nope"})
    assert hackernews.fetch() == []


def test_fetch_includes_historical_show_hn_product_pool(monkeypatch):
    def fake_get(url, params, timeout):
        if params.get("query") == "Show HN:":
            return _Resp({"hits": [{
                "title": "Show HN: Durable product",
                "story_text": "Used by teams",
                "url": "https://product.example",
                "points": 88,
                "objectID": "show-1",
                "created_at": "2024-01-01T00:00:00Z",
            }]})
        return _Resp({"hits": []})

    monkeypatch.setattr(hackernews.requests, "get", fake_get)
    out = hackernews.fetch()

    assert len(out) == 1
    assert out[0]["opportunity_type"] == "已有成果产品"
    assert out[0]["published_at"].startswith("2024-")
