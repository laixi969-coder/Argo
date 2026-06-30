import pytest
import requests

from src import llm


def test_interactive_chat_does_not_retry_until_serverless_timeout(monkeypatch):
    calls = []

    def boom(*args, **kwargs):
        calls.append(kwargs["timeout"])
        raise requests.Timeout("slow")

    monkeypatch.setattr(llm.requests, "post", boom)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    with pytest.raises(requests.Timeout):
        llm.chat_llm([{"role": "user", "content": "hi"}], timeout=60)
    assert calls == [20, 20]
