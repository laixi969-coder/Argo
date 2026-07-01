import pytest

from src.sources import huggingface


class _Resp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_fetch_parses_runnable_agent_demo(monkeypatch):
    payload = [{
        "id": "ibm/cuga-apps",
        "cardData": {"title": "CUGA Apps", "short_description": "Real-life agents"},
        "likes": 53,
        "trendingScore": 80,
        "sdk": "gradio",
        "tags": ["agents", "mcp-server"],
        "createdAt": "2026-06-30T00:00:00Z",
    }]
    monkeypatch.setattr(huggingface.requests, "get", lambda *a, **k: _Resp(payload))

    out = huggingface.fetch()

    assert out[0]["opportunity_type"] == "Agent 成果"
    assert out[0]["is_outcome"] is True
    assert out[0]["signal"] == 80
    assert out[0]["url"].endswith("/ibm/cuga-apps")


def test_fetch_rejects_bad_payload(monkeypatch):
    monkeypatch.setattr(huggingface.requests, "get", lambda *a, **k: _Resp({"error": "bad"}))
    with pytest.raises(RuntimeError, match="返回异常"):
        huggingface.fetch()
