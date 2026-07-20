from src import kv, traffic


def test_size_guard_rejects_large_body_and_path():
    assert traffic.size_decision(raw_path="/api/chat", content_length=traffic.MAX_BODY_BYTES + 1).status == 413
    assert traffic.size_decision(raw_path="/" + "x" * traffic.MAX_PATH_BYTES, content_length=0).status == 414
    assert traffic.size_decision(raw_path="/daily", content_length=0) is None


def test_costly_chat_fails_closed_on_vercel_when_kv_unavailable(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(kv, "fixed_window", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    decision = traffic.check("POST", "/api/chat", "203.0.113.9")
    assert not decision.allowed
    assert decision.status == 503


def test_non_costly_request_uses_memory_fallback(monkeypatch):
    traffic._reset_for_tests()
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(kv, "fixed_window", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    for _ in range(240):
        assert traffic.check("GET", "/daily", "203.0.113.10").allowed
    blocked = traffic.check("GET", "/daily", "203.0.113.10")
    assert not blocked.allowed
    assert blocked.status == 429
    assert blocked.retry_after > 0


def test_kv_fixed_window_uses_atomic_increment(monkeypatch):
    seen = {}

    def fake_command(*args):
        seen["args"] = args
        return [13, 42]

    monkeypatch.setattr(kv, "command", fake_command)
    allowed, retry = kv.fixed_window("chat:hash", limit=12, window=60)
    assert not allowed
    assert retry == 42
    assert seen["args"][0] == "EVAL"
    assert seen["args"][-1] == 60
