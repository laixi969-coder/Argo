import json
from datetime import date, timedelta
from src import dedup


def _opps(urls):
    return [{"url": u, "signal": float(i)} for i, u in enumerate(urls)]


def test_filter_fresh_prefers_unseen(tmp_path, monkeypatch):
    seen = tmp_path / "seen.json"
    seen.write_text(json.dumps({"http://a": date.today().isoformat()}))
    monkeypatch.setattr(dedup, "SEEN", seen)
    out = dedup.filter_fresh(_opps(["http://a", "http://b", "http://c"]), min_keep=2)
    urls = [o["url"] for o in out]
    assert "http://a" not in urls  # 近期推过的被滤掉
    assert "http://b" in urls and "http://c" in urls


def test_filter_fresh_backfills_when_too_few(tmp_path, monkeypatch):
    seen = tmp_path / "seen.json"
    seen.write_text(json.dumps({u: date.today().isoformat() for u in ["http://a", "http://b"]}))
    monkeypatch.setattr(dedup, "SEEN", seen)
    out = dedup.filter_fresh(_opps(["http://a", "http://b", "http://c"]), min_keep=3)
    # 只有 c 是新的，但 min_keep=3，用旧的回退补满，保证不空
    assert len(out) == 3


def test_expired_seen_counts_as_fresh(tmp_path, monkeypatch):
    seen = tmp_path / "seen.json"
    old = (date.today() - timedelta(days=30)).isoformat()
    seen.write_text(json.dumps({"http://a": old}))
    monkeypatch.setattr(dedup, "SEEN", seen)
    out = dedup.filter_fresh(_opps(["http://a"]), min_keep=1)
    assert out[0]["url"] == "http://a"  # 超 TTL，又算新的


def test_mark_seen_writes_and_prunes(tmp_path, monkeypatch):
    seen = tmp_path / "seen.json"
    old = (date.today() - timedelta(days=30)).isoformat()
    seen.write_text(json.dumps({"http://old": old}))
    monkeypatch.setattr(dedup, "SEEN", seen)
    dedup.mark_seen(_opps(["http://new"]))
    data = json.loads(seen.read_text())
    assert "http://new" in data
    assert "http://old" not in data  # 过期项被清理
