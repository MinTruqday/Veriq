import calendar
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo


def occurrence(first_run_at, cadence, interval, index, zone):
    local = first_run_at.astimezone(ZoneInfo(zone))
    step = interval * index
    if cadence == "ONCE":
        return first_run_at if index == 0 else None
    if cadence == "HOUR":
        return first_run_at.astimezone(timezone.utc) + timedelta(hours=step)
    if cadence in {"DAY", "WEEK"}:
        target = local + timedelta(days=step * (7 if cadence == "WEEK" else 1))
    else:
        months = step * {"MONTH": 1, "QUARTER": 3, "YEAR": 12}[cadence]
        month_index = local.year * 12 + local.month - 1 + months
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        target = local.replace(year=year, month=month, day=min(local.day, calendar.monthrange(year, month)[1]))
    normalized = target.astimezone(timezone.utc).astimezone(ZoneInfo(zone))
    return normalized.astimezone(timezone.utc)


def latest_due(schedule, timestamp):
    first = schedule["first_run_at"]
    cadence, interval = schedule["cadence"], schedule["interval"]
    zone = schedule["report"]["period"]["timezone"]
    start = int(schedule.get("next_index", 0))
    first_due = occurrence(first, cadence, interval, start, zone)
    if first_due is None or first_due > timestamp:
        return None
    if cadence == "ONCE":
        return start, first_due, None
    low, high = start, start + 1
    while occurrence(first, cadence, interval, high, zone) <= timestamp:
        low, high = high, high * 2 + 1
    while low + 1 < high:
        middle = (low + high) // 2
        if occurrence(first, cadence, interval, middle, zone) <= timestamp:
            low = middle
        else:
            high = middle
    return low, occurrence(first, cadence, interval, low, zone), occurrence(first, cadence, interval, low + 1, zone)
