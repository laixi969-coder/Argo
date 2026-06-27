import json

import pytest

from src.admin import (
    fetch_models,
    merged_settings,
    safe_settings,
    save_settings,
    test_data_provider as check_data_provider,
    test_llm as check_llm,
    test_tikhub as check_tikhub,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_safe_settings_never_returns_secrets():
    result = safe_settings({"LLM_BASE_URL": "https://x/v1", "LLM_API_KEY": "secret"})

    assert result["LLM_BASE_URL"] == "https://x/v1"
    assert "LLM_API_KEY" not in {key for key in result if key != "configured"}
    assert result["configured"]["LLM_API_KEY"] is True
    assert "secret" not in json.dumps(result)


def test_blank_secret_preserves_existing_value(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_BASE_URL=https://old/v1\nLLM_API_KEY=keep-me\n", encoding="utf-8")

    save_settings({"LLM_BASE_URL": "https://new/v1", "LLM_API_KEY": ""}, env)
    merged = merged_settings({"LLM_API_KEY": ""}, env)

    assert "LLM_BASE_URL=https://new/v1" in env.read_text(encoding="utf-8")
    assert "LLM_API_KEY=keep-me" in env.read_text(encoding="utf-8")
    assert merged["LLM_API_KEY"] == "keep-me"


def test_save_rejects_env_line_injection(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_MODEL=old\n", encoding="utf-8")

    with pytest.raises(ValueError):
        save_settings({"LLM_MODEL": "safe\nADMIN_EMAIL=attacker"}, env)


def test_fetch_models_uses_base_url_and_returns_sorted_ids():
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        seen["headers"] = kwargs["headers"]
        return FakeResponse({"data": [{"id": "z-model"}, {"id": "a-model"}]})

    models = fetch_models(
        {"LLM_BASE_URL": "https://api.example/v1/", "LLM_API_KEY": "key"},
        get=fake_get,
    )

    assert models == ["a-model", "z-model"]
    assert seen["url"] == "https://api.example/v1/models"
    assert seen["headers"]["Authorization"] == "Bearer key"


def test_llm_connection_uses_selected_model():
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(url=url, json=kwargs["json"])
        return FakeResponse({"choices": [{"message": {"content": "OK"}}]})

    message = check_llm(
        {"LLM_BASE_URL": "https://api.example/v1", "LLM_API_KEY": "key", "LLM_MODEL": "argo-model"},
        post=fake_post,
    )

    assert seen["url"].endswith("/chat/completions")
    assert seen["json"]["model"] == "argo-model"
    assert "连接成功" in message


def test_generic_data_provider_uses_configured_auth_and_endpoint():
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(url=url, headers=kwargs["headers"])
        response = FakeResponse({"ok": True})
        response.status_code = 200
        return response

    message = check_data_provider(
        {
            "TIKHUB_BASE_URL": "https://data.example/v1/",
            "TIKHUB_API_KEY": "secret",
            "TIKHUB_TEST_PATH": "/account",
            "TIKHUB_AUTH_HEADER": "X-API-Key",
            "TIKHUB_AUTH_PREFIX": "",
        },
        "TIKHUB",
        "TikHub",
        get=fake_get,
    )

    assert seen["url"] == "https://data.example/v1/account"
    assert seen["headers"] == {"X-API-Key": "secret"}
    assert "HTTP 200" in message


def test_tikhub_uses_official_account_endpoint_and_reports_credit():
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(url=url, headers=kwargs["headers"])
        return FakeResponse({
            "code": 200,
            "api_key_data": {"api_key_status": 1},
            "user_data": {
                "balance": 12.5,
                "free_credit": 0.5,
                "account_disabled": False,
                "is_active": True,
            },
        })

    message = check_tikhub(
        {"TIKHUB_BASE_URL": "https://api.tikhub.io", "TIKHUB_API_KEY": "secret"},
        get=fake_get,
    )

    assert seen["url"] == "https://api.tikhub.io/api/v1/tikhub/user/get_user_info"
    assert seen["headers"] == {"Authorization": "Bearer secret"}
    assert "余额 12.5" in message
    assert "免费额度 0.5" in message
