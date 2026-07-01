import pytest

from src.sources import futurepedia


def test_parse_extracts_verified_agent_product():
    html = (
        r'\"toolName\":\"Factory Agent\",'
        r'\"toolShortDescription\":\"Diagnoses equipment failures.\",'
        r'\"verified\":true,\"websiteUrl\":\"https://agent.example/?a=1\u0026b=2\"'
    )

    out = futurepedia._parse(html, "ai-agents")

    assert out[0]["title"] == "Factory Agent"
    assert out[0]["url"] == "https://agent.example/?a=1&b=2"
    assert out[0]["opportunity_type"] == "Agent 成果"
    assert out[0]["signal"] == 70


def test_fetch_rejects_empty_directory(monkeypatch):
    monkeypatch.setattr(futurepedia, "_fetch_page", lambda slug: [])
    with pytest.raises(RuntimeError, match="无可用产品"):
        futurepedia.fetch()
