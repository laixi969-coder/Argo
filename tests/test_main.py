import json
import pytest
from src import main


def _wire(monkeypatch, tmp_path, sources):
    """把 main 的外部依赖全换成假的，只测编排逻辑。"""
    monkeypatch.setattr(main, "SOURCES", sources)
    monkeypatch.setattr(main, "REPORT", tmp_path / "latest_report.json")
    monkeypatch.setattr(main.extract, "extract_ideas",
                        lambda opps, **k: [dict(o, idea=o["title"]) for o in opps])
    monkeypatch.setattr(main.score, "score_real_demand",
                        lambda opps, **k: [dict(o, verdict="真需求", score=70.0, reason="r") for o in opps])
    monkeypatch.setattr(main.dedup, "filter_fresh", lambda opps, **k: opps)
    monkeypatch.setattr(main.store, "append", lambda final, **k: None)  # 不写真实 data
    seen = {}
    monkeypatch.setattr(main.dedup, "mark_seen", lambda final: seen.update({"called": final}))
    sent = {}
    monkeypatch.setattr(main, "_deliver",
                        lambda final, missing: sent.update({"final": final, "missing": missing}))
    return sent, seen


def _fake_opps(n, src="producthunt"):
    return [{"source": src, "title": f"机会{i}", "raw_text": "", "url": f"http://x/{i}",
             "signal": float(n - i)} for i in range(n)]


def test_run_full_flow_pushes_and_marks(monkeypatch, tmp_path):
    sent, seen = _wire(monkeypatch, tmp_path, {"producthunt": lambda: _fake_opps(5)})
    main.run()
    assert len(sent["final"]) == 5
    assert sent["missing"] == []            # 没有缺源
    assert "called" in seen                 # 推送成功后登记了
    saved = json.loads((tmp_path / "latest_report.json").read_text())
    assert len(saved) == 5                  # 存盘了供 bot 读


def test_run_degrades_on_source_failure(monkeypatch, tmp_path):
    def boom():
        raise RuntimeError("源挂了")
    sent, seen = _wire(monkeypatch, tmp_path, {
        "producthunt": lambda: _fake_opps(3),
        "reddit": boom,
    })
    main.run()
    assert "reddit" in sent["missing"]      # 挂掉的源被标注，整条不崩
    assert len(sent["final"]) == 3          # 活着的源照常出片


def test_run_all_sources_dead_sends_empty(monkeypatch, tmp_path):
    def boom():
        raise RuntimeError("全挂")
    sent, seen = _wire(monkeypatch, tmp_path, {"producthunt": boom})
    with pytest.raises(RuntimeError, match="所有数据源"):
        main.run()
    assert sent["final"] == []              # 无机会也推一条（标注缺源）
    assert "producthunt" in sent["missing"]


def test_run_rejects_concurrent_cloud_pipeline(monkeypatch):
    monkeypatch.setattr(main.kv, "enabled", lambda: True)
    monkeypatch.setattr(main.kv, "acquire_lock", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="并发覆盖"):
        main.run()


def test_run_releases_cloud_lock_on_failure(monkeypatch):
    released = []
    monkeypatch.setattr(main.kv, "enabled", lambda: True)
    monkeypatch.setattr(main.kv, "acquire_lock", lambda *a, **k: True)
    monkeypatch.setattr(main.kv, "release_lock", lambda name, owner: released.append((name, owner)))
    monkeypatch.setattr(main, "_run_unlocked", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        main.run()
    assert released and released[0][0] == "daily-pipeline"
