import json
from src import demo


def test_demo_runs_full_chain_and_renders():
    text = demo.run_demo()
    # 渲染出最终 Telegram 文案，含标题和机会判定
    assert "金羊毛 Argo" in text
    assert "真需求" in text


def test_demo_writes_latest_report():
    demo.run_demo()
    assert demo.REPORT.exists()
    data = json.loads(demo.REPORT.read_text())
    assert data and all("idea" in o and "verdict" in o for o in data)


def test_demo_drops_no_fake_demand():
    # 六条里一条伪需求被过滤，五条应入榜
    demo.run_demo()
    data = json.loads(demo.REPORT.read_text())
    assert len(data) == 5
