"""存储边界校验：没走过完整流水线的裸对象不得进入公开历史。

背景：一条 {"idea":"x","url":"http://x","score":80} 的测试残留曾混进生产 KV，
被 enrich 补齐字段后以 80 分高潜力挂上公开站。写入与读取两侧都必须拒收。
"""
import json
import pytest
from src import store


FULL = {"idea": "发票工具", "verdict": "真需求", "score": 80, "reason": "刚需",
        "source": "reddit", "url": "https://reddit.com/r/a"}
NAKED = {"idea": "x", "url": "http://x", "score": 80, "is_ai_application": True}


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(store, "LATEST", tmp_path / "latest.json")


def test_naked_object_is_not_publishable():
    assert store.is_publishable(FULL) is True
    assert store.is_publishable(NAKED) is False
    assert store.is_publishable({**FULL, "reason": ""}) is False
    assert store.is_publishable({**FULL, "idea": "未知"}) is False
    assert store.is_publishable({**FULL, "idea": "x"}) is False
    assert store.is_publishable({**FULL, "url": ""}) is False
    # 精判失败的合法旧数据（无 verdict/source 但有 reason）必须保留
    legacy = {"idea": "热门但没精判", "url": "https://x.com", "score": 100,
              "reason": "真需求精判失败，按源头信号保留"}
    assert store.is_publishable(legacy) is True


def test_append_drops_naked_objects(tmp_path):
    store.append([dict(FULL), dict(NAKED)], day="2026-07-11")
    opps = store.load_day("2026-07-11")
    assert [o["idea"] for o in opps] == ["发票工具"]


def test_load_filters_polluted_history(tmp_path):
    # 模拟历史上已被污染的快照：读取侧也要能兜住
    store.HISTORY.mkdir(parents=True)
    (store.HISTORY / "2026-07-11.json").write_text(json.dumps(
        [dict(FULL, id="a", date="2026-07-11"),
         dict(NAKED, id="b", date="2026-07-11")], ensure_ascii=False))
    opps = store.load_day("2026-07-11")
    assert [o["idea"] for o in opps] == ["发票工具"]
