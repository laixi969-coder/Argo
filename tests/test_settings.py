from src.settings import (
    _is_configured,
    _read_values,
    _replace_value,
    hash_password,
    verify_password,
)


def test_placeholder_and_empty_values_are_not_configured():
    assert not _is_configured("")
    assert not _is_configured("CHANGE_ME")
    assert _is_configured("real-value")


def test_replace_value_preserves_other_settings(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_MODEL=old\nREPORT_TO=a@example.com\n", encoding="utf-8")

    _replace_value("LLM_MODEL", "new-model", env)

    values = _read_values(env)
    assert values["LLM_MODEL"] == "new-model"
    assert values["REPORT_TO"] == "a@example.com"
    assert env.stat().st_mode & 0o777 == 0o600


def test_admin_password_is_hashed_and_verified():
    encoded = hash_password("correct horse", salt=b"0123456789abcdef", iterations=10)

    assert "correct horse" not in encoded
    assert verify_password("correct horse", encoded)
    assert not verify_password("wrong horse", encoded)
