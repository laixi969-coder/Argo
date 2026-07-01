from src import doctor


def test_missing_required_detects_blanks(monkeypatch):
    monkeypatch.setattr(doctor.config, "get", lambda k, d=None: "")
    miss = doctor.missing_required()
    assert miss == ["LLM_API_KEY"]
    assert "TELEGRAM_BOT_TOKEN" not in miss
    assert "PRODUCTHUNT_TOKEN" not in miss
    assert "REDDIT_CLIENT_ID" not in miss  # 可选项不算缺


def test_all_set_reports_ready(monkeypatch):
    monkeypatch.setattr(doctor.config, "get", lambda k, d=None: "filled")
    assert doctor.missing_required() == []
    assert doctor.report() is True
