from datetime import datetime, timezone

from src import clock


def test_business_date_uses_shanghai_not_utc():
    utc_late = datetime(2026, 6, 29, 16, 30, tzinfo=timezone.utc)
    assert clock.today_iso(utc_late) == "2026-06-30"
