import json
import pytest
from src import feedback, bot_admin as admin


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "REPORT", tmp_path / "latest_report.json")
    monkeypatch.setattr(feedback, "FEEDBACK", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(feedback, "DATA", tmp_path)
    (tmp_path / "latest_report.json").write_text(json.dumps([
        {"idea": "发票工具", "verdict": "真需求", "score": 80, "url": "http://x"},
        {"idea": "宠物排班", "verdict": "待验证", "score": 60, "url": "http://y"},
    ]))


def test_record_good_appends(tmp_path):
    out = feedback.record(1, "good", "我愿意付钱")
    assert "好机会" in out and "发票工具" in out
    line = json.loads((tmp_path / "feedback.jsonl").read_text().strip())
    assert line["label"] == "good" and line["idea"] == "发票工具" and line["note"] == "我愿意付钱"


def test_record_out_of_range():
    assert "没有第 9 条" in feedback.record(9, "bad")


def test_admin_routes_good_command():
    out = admin.handle("/good 2")
    assert "宠物排班" in out


def test_admin_good_bad_usage():
    assert "用法" in admin.handle("/good")
    assert "用法" in admin.handle("/bad abc")
