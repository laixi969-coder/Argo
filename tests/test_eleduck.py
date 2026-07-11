from datetime import datetime, timedelta, timezone

from src.sources import eleduck


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _recent(days=1):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _patch(monkeypatch, payload_by_category):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _Resp({"posts": payload_by_category.get(params["category"], [])})
    monkeypatch.setattr(eleduck.requests, "get", fake_get)


def test_fetch_parses_posts(monkeypatch):
    _patch(monkeypatch, {15: [
        {"id": "abc", "title": "做了个英语记忆小程序", "summary": "痛点是记不住",
         "published_at": _recent(), "upvotes_count": 3, "comments_count": 7},
    ]})
    out = eleduck.fetch()
    assert len(out) == 1
    o = out[0]
    assert o["source"] == "eleduck" and o["url"] == "https://eleduck.com/posts/abc"
    assert o["is_outcome"] is True and o["signal"] == 65.0


def test_fetch_drops_stale_pinned_posts(monkeypatch):
    _patch(monkeypatch, {15: [
        {"id": "old", "title": "2022 年置顶帖", "published_at": "2022-05-13T17:49:28.029+08:00"},
        {"id": "new", "title": "新帖", "published_at": _recent()},
    ]})
    out = eleduck.fetch()
    assert [o["url"] for o in out] == ["https://eleduck.com/posts/new"]


def test_hiring_posts_are_demand_signals(monkeypatch):
    _patch(monkeypatch, {5: [
        {"id": "job", "title": "招远程 Python 开发", "published_at": _recent()},
    ]})
    out = eleduck.fetch()
    assert out[0]["opportunity_type"] == "需求信号" and out[0]["is_outcome"] is False


def test_fetch_degrades_when_category_fails(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _Resp({"error": "nope"})
    monkeypatch.setattr(eleduck.requests, "get", fake_get)
    assert eleduck.fetch() == []
