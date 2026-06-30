import json
from src import agent


def test_load_report_formats_lines(tmp_path, monkeypatch):
    rpt = tmp_path / "latest_report.json"
    rpt.write_text(json.dumps([
        {"idea": "发票工具", "verdict": "真需求", "score": 80,
         "reason": "刚需", "url": "http://x", "source": "reddit"}
    ]))
    monkeypatch.setattr(agent, "REPORT", rpt)
    out = agent.load_report()
    assert "发票工具" in out and "真需求" in out and "1." in out


def test_load_report_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "REPORT", tmp_path / "nope.json")
    assert "还没有榜单" in agent.load_report()


def test_handle_message_discusses_with_context(tmp_path, monkeypatch):
    rpt = tmp_path / "latest_report.json"
    rpt.write_text(json.dumps([
        {"idea": "宠物排班器", "verdict": "真需求", "score": 64,
         "reason": "r", "url": "http://x", "source": "reddit"}
    ]))
    monkeypatch.setattr(agent, "REPORT", rpt)
    monkeypatch.setattr(agent, "CHAT_LOG", tmp_path / "chat.jsonl")
    captured = {}

    def fake_chat(m):
        captured["m"] = m
        return "我的看法是…"

    monkeypatch.setattr(agent.llm, "chat_llm", fake_chat)
    agent._sessions.clear()
    out = agent.handle_message("第 1 条深挖", user_id="u1")
    assert out == "我的看法是…"
    system = captured["m"][0]["content"]
    assert "宠物排班器" in system and "价值" in system


def test_handle_message_routes_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "CHAT_LOG", tmp_path / "chat.jsonl")
    monkeypatch.setattr(agent.admin.config, "OVERRIDES", tmp_path / "config.json")
    out = agent.handle_message("/model gpt-5.5", user_id="u1")
    assert "gpt-5.5" in out  # 命令走后台，没调 LLM


def test_handle_message_isolates_user_history(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "REPORT", tmp_path / "nope.json")
    monkeypatch.setattr(agent, "CHAT_LOG", tmp_path / "chat.jsonl")
    monkeypatch.setattr(agent.llm, "chat_llm", lambda m: "ok")
    agent._sessions.clear()
    agent.handle_message("hi", user_id="A")
    agent.handle_message("hi", user_id="B")
    # 两个用户各自独立的会话历史（商业化多用户的缝）
    assert "A" in agent._sessions and "B" in agent._sessions
    assert agent._sessions["A"] is not agent._sessions["B"]


def test_handle_message_catches_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "REPORT", tmp_path / "nope.json")
    monkeypatch.setattr(agent, "CHAT_LOG", tmp_path / "chat.jsonl")
    def boom(m):
        raise RuntimeError("LLM 挂了")
    monkeypatch.setattr(agent.llm, "chat_llm", boom)
    agent._sessions.clear()
    out = agent.handle_message("聊聊", user_id="u1")
    assert "暂时不可用" in out  # 不抛、不泄露底层异常，返回人话


def test_handle_message_survives_log_storage_failure(monkeypatch):
    """Vercel 文件系统不可写时，日志失败不能拖垮聊天主链路。"""
    monkeypatch.setattr(agent, "log_turn", lambda *a, **k: (_ for _ in ()).throw(OSError("read-only")))
    monkeypatch.setattr(agent.llm, "chat_llm", lambda messages: "回答正常")
    monkeypatch.setattr(agent, "load_report", lambda: "1. 测试机会")
    agent._sessions.clear()

    assert agent.handle_message("测试问题", user_id="u1") == "回答正常"


def test_cloud_chat_recovers_history_and_logs_by_user(monkeypatch):
    logged, captured = [], {}
    monkeypatch.setattr(agent.kv, "enabled", lambda: True)
    monkeypatch.setattr(agent.kv, "list_json", lambda *a, **k: [
        {"role": "user", "text": "上一问"}, {"role": "assistant", "text": "上一答"}
    ])
    monkeypatch.setattr(agent.kv, "append_json", lambda key, value, **k: logged.append((key, value)))
    monkeypatch.setattr(agent, "load_report", lambda: "1. 测试机会")
    def fake_chat(messages):
        captured["messages"] = messages
        return "新回答"

    monkeypatch.setattr(agent.llm, "chat_llm", fake_chat)

    assert agent.handle_message("新问题", user_id="user-a") == "新回答"
    messages = captured["messages"]
    assert [m["content"] for m in messages[-3:]] == ["上一问", "上一答", "新问题"]
    assert len(logged) == 2 and logged[0][0] == logged[1][0]
