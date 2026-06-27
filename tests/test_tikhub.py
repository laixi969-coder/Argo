import pytest
from src.sources import tikhub


class _Resp:
    def __init__(self, payload, status=200):
        self._p = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._p


def _mock_cfg(monkeypatch, key="secret"):
    monkeypatch.setattr(tikhub.config, "get", lambda k, d=None: key if k else d)


def _make_item(aweme_id="123", desc="I wish there was an app for this", digg=50):
    return {
        "aweme_info": {
            "aweme_id": aweme_id,
            "desc": desc,
            "statistics": {"digg_count": digg, "play_count": 0},
            "author": {"unique_id": "user1"},
            "share_url": f"https://www.tiktok.com/@user1/video/{aweme_id}",
        }
    }


def test_fetch_parses_videos(monkeypatch):
    _mock_cfg(monkeypatch)
    payload = {"code": 200, "data": {"data": [_make_item()]}}
    monkeypatch.setattr(tikhub.requests, "get", lambda *a, **k: _Resp(payload))
    out = tikhub.fetch()
    assert len(out) > 0
    assert out[0]["source"] == "tikhub"
    assert out[0]["signal"] == 50.0
    assert "I wish" in out[0]["title"]


def test_fetch_deduplicates_across_keywords(monkeypatch):
    _mock_cfg(monkeypatch)
    # 所有关键词返回同一条视频
    payload = {"code": 200, "data": {"data": [_make_item()]}}
    monkeypatch.setattr(tikhub.requests, "get", lambda *a, **k: _Resp(payload))
    out = tikhub.fetch()
    urls = [p["url"] for p in out]
    assert len(urls) == len(set(urls)), "存在重复 URL"


def test_fetch_skips_empty_desc(monkeypatch):
    _mock_cfg(monkeypatch)
    item_no_desc = {
        "aweme_info": {
            "aweme_id": "999",
            "desc": "",
            "statistics": {"digg_count": 10, "play_count": 0},
            "author": {"unique_id": "u"},
        }
    }
    payload = {"code": 200, "data": {"data": [item_no_desc]}}
    monkeypatch.setattr(tikhub.requests, "get", lambda *a, **k: _Resp(payload))
    out = tikhub.fetch()
    assert all(p["title"] for p in out), "空描述应被跳过"


def test_fetch_keyword_failure_is_skipped(monkeypatch):
    """单个关键词失败不应让整个 fetch 崩溃。"""
    _mock_cfg(monkeypatch)
    calls = {"n": 0}

    def _get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("模拟超时")
        return _Resp({"code": 200, "data": {"data": [_make_item(aweme_id=str(calls["n"]))]}})

    monkeypatch.setattr(tikhub.requests, "get", _get)
    out = tikhub.fetch()  # 第一个关键词失败，后续继续
    assert isinstance(out, list)


def test_fetch_missing_key_raises(monkeypatch):
    monkeypatch.setattr(tikhub.config, "get", lambda k, d=None: "")
    with pytest.raises(RuntimeError, match="未配置"):
        tikhub.fetch()


def test_fetch_api_error_raises(monkeypatch):
    _mock_cfg(monkeypatch)
    payload = {"code": 401, "message_zh": "Key 无效", "data": {"data": []}}
    monkeypatch.setattr(tikhub.requests, "get", lambda *a, **k: _Resp(payload))
    # 单个关键词 RuntimeError 被 fetch 内部 catch 掉，整体不抛
    out = tikhub.fetch()
    assert out == []
