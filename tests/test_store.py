import json

from src import store


def test_empty_rerun_keeps_existing_local_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(store.kv, "enabled", lambda: False)

    store.append([{"idea": "已有机会", "url": "https://reddit.com/r/1"}], day="2026-06-30")
    store.append([], day="2026-06-30")

    saved = json.loads((store.HISTORY / "2026-06-30.json").read_text())
    assert [o["idea"] for o in saved] == ["已有机会"]


def test_three_runs_merge_same_day_without_losing_history(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(store.kv, "enabled", lambda: False)

    store.append([{"idea": "早班", "url": "https://reddit.com/r/a", "score": 70}], day="2026-06-30")
    store.append([{"idea": "午班", "url": "https://reddit.com/r/b", "score": 90}], day="2026-06-30")
    store.append([{"idea": "晚班", "url": "https://reddit.com/r/c", "score": 80}], day="2026-06-30")

    saved = json.loads((store.HISTORY / "2026-06-30.json").read_text())
    assert [o["idea"] for o in saved] == ["午班", "晚班", "早班"]


def test_empty_day_is_visible_in_cloud_history(monkeypatch):
    monkeypatch.setattr(store.kv, "enabled", lambda: True)
    monkeypatch.setattr(store.kv, "smembers", lambda key: ["2026-06-30", "2026-06-29"])
    snapshots = {"history:2026-06-30": [], "history:2026-06-29": [{"idea": "昨天"}]}
    monkeypatch.setattr(store.kv, "get_json", lambda key: snapshots[key])

    assert store.load_days() == [
        ("2026-06-30", []),
        ("2026-06-29", [{"idea": "昨天"}]),
    ]


def test_empty_rerun_keeps_existing_cloud_snapshot(monkeypatch):
    calls = []
    monkeypatch.setattr(store.kv, "enabled", lambda: True)
    monkeypatch.setattr(store.kv, "get_json", lambda key: [{"idea": "已有机会"}])
    monkeypatch.setattr(store.kv, "set_json", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(store.kv, "sadd", lambda *args: calls.append(args))

    store.append([], day="2026-06-30")

    assert calls == []


def test_cloud_rerun_merges_existing_snapshot(monkeypatch):
    written = {}
    monkeypatch.setattr(store.kv, "enabled", lambda: True)
    monkeypatch.setattr(
        store.kv,
        "get_json",
        lambda key: [{"idea": "早班", "url": "https://reddit.com/r/a", "id": "old", "date": "2026-06-30", "score": 70}],
    )
    monkeypatch.setattr(store.kv, "set_json", lambda key, value: written.update({key: value}))
    monkeypatch.setattr(store.kv, "sadd", lambda *args: None)

    store.append([{"idea": "午班", "url": "https://reddit.com/r/b", "score": 90}], day="2026-06-30")

    assert [o["idea"] for o in written["history:2026-06-30"]] == ["午班", "早班"]


def test_production_reads_and_merges_never_expose_demo_items(monkeypatch):
    monkeypatch.setattr(store.kv, "enabled", lambda: True)
    fake = {"idea": "演示", "url": "https://example.com/0", "date": "2026-06-30"}
    real = {"idea": "真实", "url": "https://reddit.com/r/x", "date": "2026-06-30"}
    monkeypatch.setattr(store.kv, "get_json", lambda key: [fake, real])
    monkeypatch.setattr(store.kv, "smembers", lambda key: ["2026-06-30"])

    assert [o["idea"] for o in store.load_day("2026-06-30")] == ["真实"]
    assert [o["idea"] for o in store.load_days()[0][1]] == ["真实"]
    assert [o["idea"] for o in store._merge([fake], [real], "2026-06-30")] == ["真实"]
