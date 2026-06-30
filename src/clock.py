"""Argo 业务时钟：所有“今天”统一按北京时间计算。"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Shanghai")


def now(value: datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(TZ)
    if value.tzinfo is None:
        return value.replace(tzinfo=TZ)
    return value.astimezone(TZ)


def today_iso(value: datetime | None = None) -> str:
    return now(value).date().isoformat()
