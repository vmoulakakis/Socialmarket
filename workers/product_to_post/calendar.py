from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any

ATHENS = ZoneInfo("Europe/Athens")

CADENCE = {
    "instagram": {"weekdays": [0,2,4,6], "hour": 12, "minute": 30},
    "facebook": {"weekdays": [1,3,5,6], "hour": 19, "minute": 0},
    "tiktok": {"weekdays": [0,1,3,5,6], "hour": 20, "minute": 30},
    "linkedin": {"weekdays": [1,3], "hour": 9, "minute": 30},
}


def build_calendar(variants: list[dict[str, Any]], horizon_days: int, start: datetime | None = None) -> list[dict[str, Any]]:
    start_local = (start or datetime.now(ATHENS)).astimezone(ATHENS)
    first_day = (start_local + timedelta(days=1)).date()
    by_platform: dict[str, list[dict[str, Any]]] = {}
    for v in variants:
        by_platform.setdefault(v["platform"], []).append(v)
    out: list[dict[str, Any]] = []
    for platform, rows in by_platform.items():
        cfg = CADENCE.get(platform)
        if not cfg or not rows:
            continue
        cursor = first_day
        index = 0
        end = first_day + timedelta(days=horizon_days)
        while cursor < end:
            if cursor.weekday() in cfg["weekdays"]:
                local_dt = datetime(cursor.year,cursor.month,cursor.day,cfg["hour"],cfg["minute"],tzinfo=ATHENS)
                variant = rows[index % len(rows)]
                out.append({
                    "platform": platform,
                    "variant_id": variant["id"],
                    "scheduled_at": local_dt.isoformat(),
                    "objective": "conversion" if index % 3 else "qualified_click",
                    "metadata": {"planner":"calendar-strategist-v1","variant_rotation":index % len(rows)},
                })
                index += 1
            cursor += timedelta(days=1)
    return sorted(out, key=lambda x: x["scheduled_at"])
