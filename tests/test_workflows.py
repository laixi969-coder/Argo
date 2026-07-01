from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_only_canonical_workflow_has_three_daily_schedules():
    canonical = (ROOT / ".github/workflows/daily.yml").read_text()
    legacy = (ROOT / ".github/workflows/argo-daily.yml").read_text()

    assert canonical.count("- cron:") == 3
    assert 'cron: "0 23 * * *"' in canonical
    assert 'cron: "0 5 * * *"' in canonical
    assert 'cron: "0 11 * * *"' in canonical
    assert "schedule:" not in legacy
    assert "TZ: Asia/Shanghai" in canonical
    assert "python -m src.verify_daily" in canonical


def test_mac_daily_job_points_to_current_argo_and_runs_three_times():
    plist = (ROOT / "scripts/com.argo.daily.plist").read_text()

    assert "<string>/Users/caiwenbin/argo</string>" in plist
    assert "<string>src.main</string>" in plist
    assert plist.count("<key>Hour</key>") == 3
    assert "Asia/Shanghai" in plist


def test_mac_web_job_points_to_current_argo_and_python():
    plist = (ROOT / "scripts/com.argo.web.plist").read_text()

    assert "<string>/Users/caiwenbin/argo</string>" in plist
    assert "<string>src.web</string>" in plist
    assert "CommandLineTools/usr/bin/python3" in plist
    assert "<key>KeepAlive</key><true/>" in plist
