from src import smoke


def test_check_reports_ok():
    assert smoke._check("X", lambda: "good") is True


def test_check_catches_failure(capsys):
    assert smoke._check("X", lambda: (_ for _ in ()).throw(RuntimeError("boom"))) is False
    assert "boom" in capsys.readouterr().out


def test_run_all_green(monkeypatch):
    monkeypatch.setattr(smoke.llm, "call_llm", lambda p, timeout=30: "在线")
    monkeypatch.setattr(smoke.telegram, "get_me", lambda: {"username": "argo_bot"})
    monkeypatch.setattr(smoke.telegram, "send_message", lambda *a, **k: None)
    monkeypatch.setattr(smoke.producthunt, "fetch", lambda: [1, 2, 3])
    monkeypatch.setattr(smoke.config, "get", lambda k, d=None: "")  # reddit 跳过
    assert smoke.run() is True


def test_run_fails_when_core_broken(monkeypatch):
    monkeypatch.setattr(smoke.llm, "call_llm",
                        lambda p, timeout=30: (_ for _ in ()).throw(RuntimeError("no key")))
    monkeypatch.setattr(smoke.telegram, "get_me", lambda: {"username": "x"})
    monkeypatch.setattr(smoke.telegram, "send_message", lambda *a, **k: None)
    monkeypatch.setattr(smoke.producthunt, "fetch", lambda: [1])
    monkeypatch.setattr(smoke.config, "get", lambda k, d=None: "")
    assert smoke.run() is False
