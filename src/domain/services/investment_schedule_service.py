"""Occurrence math for investment schedules — pure, no I/O.

Steps a recurring rule from its start date and lists the occurrence dates that
fall in a window. Used both to materialize past-due contributions and to project
future ones onto the value charts.
"""
from calendar import monthrange
from datetime import date, timedelta
from typing import List, Optional

from src.domain.entities.investment_schedule import ScheduleFrequency


def _add_months(d: date, n: int) -> date:
    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def _step(d: date, frequency: ScheduleFrequency, interval: int) -> date:
    if frequency == ScheduleFrequency.DAILY:
        return d + timedelta(days=interval)
    if frequency == ScheduleFrequency.WEEKLY:
        return d + timedelta(weeks=interval)
    if frequency == ScheduleFrequency.MONTHLY:
        return _add_months(d, interval)
    if frequency == ScheduleFrequency.YEARLY:
        return _add_months(d, 12 * interval)
    return d + timedelta(days=interval)


def occurrences_between(
    frequency: ScheduleFrequency,
    interval: int,
    start: date,
    date_from: date,
    date_to: date,
    end: Optional[date] = None,
    max_occurrences: int = 100000,
) -> List[date]:
    """Occurrence dates in [date_from, date_to], respecting the schedule's own
    end date. Steps from `start` by frequency*interval."""
    interval = max(interval, 1)
    if end is not None and date_to > end:
        date_to = end
    result: List[date] = []
    current = start
    count = 0
    while current <= date_to and count < max_occurrences:
        if current >= date_from:
            result.append(current)
        current = _step(current, frequency, interval)
        count += 1
    return result


def next_occurrence(
    frequency: ScheduleFrequency,
    interval: int,
    start: date,
    after: date,
    end: Optional[date] = None,
    max_steps: int = 100000,
) -> Optional[date]:
    """First occurrence strictly after `after` (and not past `end`), or None."""
    interval = max(interval, 1)
    current = start
    for _ in range(max_steps):
        if end is not None and current > end:
            return None
        if current > after:
            return current
        current = _step(current, frequency, interval)
    return None

