import json
import pytest
from src import demo


@pytest.fixture(autouse=True)
def isolate_demo(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "REPORT", tmp_path / "demo" / "latest_report.json")
    monkeypatch.setattr(demo, "HISTORY", tmp_path / "demo" / "history")


def test_demo_runs_full_chain_and_renders():
    text = demo.run_demo()
    # 渲染出最终 Telegram 文案，含标题和机会判定
    assert "金羊毛 Argo" in text
    assert "真需求" in text
    assert "图生视频进入快预览阶段" in text


def test_demo_writes_latest_report():
    demo.run_demo()
    assert demo.REPORT.exists()
    data = json.loads(demo.REPORT.read_text())
    assert data and all("idea" in o and "verdict" in o for o in data)
    titles = [o["idea"] for o in data]
    assert "图生视频进入快预览阶段：内容团队可以低成本批量试镜头再筛选精修" in titles
    assert "Wan2.2 14B Fast Preview" not in titles


def test_demo_fake_llm_parses_score_evidence_json_with_escaped_idea():
    prompt = '待审材料（JSON）：\n{"idea":"Wan2.2 14B Fast Preview"}\n\n只输出 JSON，不要任何多余文字：'
    raw = json.loads(demo._fake_llm(prompt))
    assert raw["verdict"] == "真需求"
    assert raw["score"] == 79


def test_demo_drops_no_fake_demand():
    # 六条里一条伪需求被过滤，五条应入榜
    demo.run_demo()
    data = json.loads(demo.REPORT.read_text())
    assert len(data) == 5


def test_demo_never_calls_production_store(monkeypatch):
    monkeypatch.setattr(demo.store, "append", lambda *a, **k: (_ for _ in ()).throw(AssertionError("touched store")))
    demo.run_demo()
    assert sorted(p.name for p in demo.HISTORY.glob("*.json"))
