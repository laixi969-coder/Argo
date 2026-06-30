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
