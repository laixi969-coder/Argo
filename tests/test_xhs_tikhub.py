import pytest
from src.sources import xhs_tikhub


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _note(note_id="n1", title="求推荐记账工具", desc="有没有好用的记账软件",
          liked=18, comments=32, ts=1768531820):
    return {"note": {"id": note_id, "title": title, "desc": desc,
                     "liked_count": liked, "comments_count": comments,
                     "timestamp": ts}}


def _patch(monkeypatch, items, code=200):
    payload = {"code": code, "data": {"data": {"items": items}}}
    monkeypatch.setattr(xhs_tikhub.requests, "get", lambda *a, **k: _Resp(payload))
    monkeypatch.setattr(xhs_tikhub.config, "get", lambda k, d=None: "fake-key")


def test_fetch_parses_notes(monkeypatch):
    _patch(monkeypatch, [_note()])
    out = xhs_tikhub.fetch()
    assert len(out) == 1
    o = out[0]
    assert o["source"] == "xhs" and o["opportunity_type"] == "需求信号"
    assert o["url"] == "https://www.xiaohongshu.com/explore/n1"
    assert o["signal"] == 82.0  # 18 赞 + 32 评论 × 2
    assert o["published_at"].startswith("2026-01")


def test_fetch_dedups_and_skips_empty_notes(monkeypatch):
    _patch(monkeypatch, [_note(), _note(), {"note": {"id": "n2"}}, {}])
    assert len(xhs_tikhub.fetch()) == 1


def test_fetch_degrades_on_api_error(monkeypatch):
    _patch(monkeypatch, [], code=402)
    assert xhs_tikhub.fetch() == []


def test_fetch_requires_key(monkeypatch):
    monkeypatch.setattr(xhs_tikhub.config, "get", lambda k, d=None: "")
    with pytest.raises(RuntimeError, match="未配置"):
        xhs_tikhub.fetch()
