import pytest

from src.sources import industry_cases


def test_fetch_labels_each_industry_and_keeps_show_hn_as_outcome(monkeypatch):
    def fake_search(query):
        return [{
            "title": f"Show HN: {query}",
            "story_text": "A working product",
            "url": f"https://example.com/{query.replace(' ', '-')}",
            "points": 55,
            "created_at": "2026-06-30T00:00:00Z",
        }]

    monkeypatch.setattr(industry_cases, "_search", fake_search)
    out = industry_cases.fetch()

    assert len(out) == len(industry_cases.QUERIES)
    assert {o["industry_hint"] for o in out} == set(industry_cases.QUERIES)
    assert all(o["is_outcome"] is True for o in out)
    assert next(o for o in out if o["industry_hint"] == "制造业")["category"] == "AI × 工业"


def test_search_rejects_bad_payload(monkeypatch):
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"error": "bad"}

    monkeypatch.setattr(industry_cases.requests, "get", lambda *a, **k: Resp())
    with pytest.raises(RuntimeError, match="返回异常"):
        industry_cases._search("AI healthcare")
