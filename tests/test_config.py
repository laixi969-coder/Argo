import os
from src import config


def test_override_beats_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OVERRIDES", tmp_path / "config.json")
    monkeypatch.setenv("LLM_MODEL", "from-env")
    assert config.get("LLM_MODEL") == "from-env"
    config.set_override("LLM_MODEL", "from-override")
    assert config.get("LLM_MODEL") == "from-override"


def test_set_override_persists(tmp_path, monkeypatch):
    f = tmp_path / "config.json"
    monkeypatch.setattr(config, "OVERRIDES", f)
    config.set_override("LLM_API_KEY", "sk-123")
    assert f.exists()
    assert config.get("LLM_API_KEY") == "sk-123"


def test_empty_override_falls_through(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OVERRIDES", tmp_path / "config.json")
    config.set_override("LLM_MODEL", "")          # 空值不算覆盖
    monkeypatch.setenv("LLM_MODEL", "env-val")
    assert config.get("LLM_MODEL") == "env-val"


def test_get_many_reads_remote_overrides_once(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "_overrides", lambda: calls.append(1) or {"A": "remote-a"})
    monkeypatch.setenv("B", "env-b")
    assert config.get_many("A", "B") == {"A": "remote-a", "B": "env-b"}
    assert calls == [1]
