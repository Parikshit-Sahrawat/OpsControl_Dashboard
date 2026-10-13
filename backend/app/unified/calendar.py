"""Deterministic wall-calendar scheduling with explicit DST fold policy."""

from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
from croniter import croniter
from app.unified.schemas import Schedule


def expression(schedule):
    hour, minute = schedule.time.split(":")[:2]
    frequency = schedule.frequency
    if frequency == "CUSTOM":
        return schedule.cron
    if frequency == "HOURLY":
        return f"{int(minute)} * * * *"
    if frequency == "DAILY":
        return f"{int(minute)} {int(hour)} * * *"
    if frequency == "WEEKLY":
        return f"{int(minute)} {int(hour)} * * " + ",".join(
            str((d + 1) % 7) for d in sorted(schedule.weekdays)
        )
    months = "1,4,7,10" if frequency == "QUARTERLY" else "*"
    return f"{int(minute)} {int(hour)} {schedule.month_day} {months} *"


def occurrences(configuration, after, before, limit=1000):
    s = Schedule.model_validate(configuration)
    zone = ZoneInfo(s.timezone)
    local_after = after.astimezone(zone).replace(tzinfo=None)
    # Include the current wall minute to handle an ambiguous fold correctly;
    # UTC filtering and unique persisted windows prevent duplicate schedules.
    iterator = croniter(expression(s), local_after - timedelta(minutes=1))
    returned = 0
    for _ in range(limit + 1000):
        naive = iterator.get_next(datetime)
        aware = naive.replace(tzinfo=zone, fold=0 if s.dst_policy == "FIRST" else 1)
        instant = aware.astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) != naive:
            continue
        if instant <= after:
            continue
        if instant > before:
            return
        if naive.date().isoformat() in s.exceptions:
            continue
        if s.frequency == "DAILY" and naive.weekday() not in s.weekdays:
            continue
        yield instant
        returned += 1
        if returned >= limit:
            return


def next_occurrence(configuration, after):
    return next(
        occurrences(configuration, after, after + timedelta(days=400), limit=1), None
    )
