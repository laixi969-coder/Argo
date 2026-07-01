from src.sources import github


def test_fetch_deduplicates_and_marks_agent_outcome(monkeypatch):
    repo = {
        "full_name": "acme/agent",
        "description": "An agent for factories",
        "html_url": "https://github.com/acme/agent",
        "stargazers_count": 800,
        "forks_count": 30,
        "topics": ["ai-agent"],
        "created_at": "2026-06-01T00:00:00Z",
    }
    monkeypatch.setattr(github, "_search", lambda query: [repo])

    out = github.fetch()

    assert len(out) == 1
    assert out[0]["opportunity_type"] == "Agent 成果"
    assert out[0]["is_outcome"] is True
    assert out[0]["signal"] == 80


def test_fetch_keeps_working_when_one_query_fails(monkeypatch):
    calls = {"n": 0}

    def fake_search(query):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("rate limited")
        return [{
            "full_name": f"acme/repo-{calls['n']}",
            "html_url": f"https://github.com/acme/repo-{calls['n']}",
            "stargazers_count": 100,
        }]

    monkeypatch.setattr(github, "_search", fake_search)
    assert len(github.fetch()) == len(github._QUERIES) - 1
