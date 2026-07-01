import pytest
from src.sources import producthunt


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _patch(monkeypatch, payload):
    monkeypatch.setattr(producthunt.config, "get", lambda k, d=None: "tok")
    monkeypatch.setattr(producthunt.requests, "post", lambda *a, **k: _Resp(payload))


def test_fetch_parses_posts(monkeypatch):
    _patch(monkeypatch, {"data": {"posts": {"edges": [
        {"node": {"name": "Foo", "tagline": "bar", "description": "d",
                  "votesCount": 30, "url": "http://x"}}
    ]}}})
    out = producthunt.fetch()
    assert out[0]["title"] == "Foo" and out[0]["source"] == "producthunt"
    assert out[0]["signal"] == 30.0
    assert out[0]["opportunity_type"] == "已有成果产品"


def test_fetch_raises_clear_on_api_errors(monkeypatch):
    _patch(monkeypatch, {"errors": [{"message": "Field 'description' doesn't exist"}]})
    with pytest.raises(RuntimeError, match="PH API 报错"):
        producthunt.fetch()


def test_fetch_raises_on_missing_data(monkeypatch):
    _patch(monkeypatch, {"data": {}})
    with pytest.raises(RuntimeError, match="返回异常"):
        producthunt.fetch()


def test_fetch_missing_token(monkeypatch):
    monkeypatch.setattr(producthunt.config, "get", lambda k, d=None: "")
    with pytest.raises(RuntimeError, match="未配置"):
        producthunt.fetch()
