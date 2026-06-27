import pytest
from src import bot


def test_bot_imports_agent():
    # bot 只是 Telegram 适配器，业务逻辑在 agent
    assert hasattr(bot, "agent") and hasattr(bot.agent, "handle_message")


def test_run_guards_missing_token(monkeypatch):
    monkeypatch.setattr(bot.config, "get", lambda k, d=None: "")
    with pytest.raises(SystemExit):
        bot.run()
