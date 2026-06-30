import pytest

from src import verify_daily


def test_verify_accepts_real_snapshot(monkeypatch):
    monkeypatch.setattr(verify_daily.store, "load_day", lambda day, **kwargs: [
        {"id": "abc", "date": day, "idea": "真实机会", "score": 80,
         "url": "https://reddit.com/r/x"}
    ])
    assert verify_daily.verify("2026-06-30") == 1


def test_verify_rejects_missing_snapshot(monkeypatch):
    monkeypatch.setattr(verify_daily.store, "load_day", lambda day, **kwargs: None)
    with pytest.raises(RuntimeError, match="历史缺失"):
        verify_daily.verify("2026-06-30")


def test_verify_rejects_demo_pollution(monkeypatch):
    monkeypatch.setattr(verify_daily.store, "load_day", lambda day, **kwargs: [
        {"id": "abc", "date": day, "idea": "假机会", "url": "https://example.com/0"}
    ])
    with pytest.raises(RuntimeError, match="demo"):
        verify_daily.verify("2026-06-30")


@pytest.mark.parametrize("item, message", [
    ({"id": "a", "date": "2026-06-30", "idea": "x", "score": "bad", "url": "https://x.com"}, "分数"),
    ({"id": "a", "date": "2026-06-30", "idea": "x", "score": 101, "url": "https://x.com"}, "越界"),
    ({"id": "a", "date": "2026-06-30", "idea": "x", "score": 50, "url": "javascript:x"}, "URL"),
])
def test_verify_rejects_malformed_history(monkeypatch, item, message):
    monkeypatch.setattr(verify_daily.store, "load_day", lambda day, **kwargs: [item])
    with pytest.raises(RuntimeError, match=message):
        verify_daily.verify("2026-06-30")
