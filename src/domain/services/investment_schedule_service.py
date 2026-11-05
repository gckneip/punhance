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


def _occurrence(
    start: date, frequency: ScheduleFrequency, interval: int, n: int
) -> date:
    """The n-th occurrence (n>=0) anchored to `start`.

    Anchoring every occurrence to the original start (rather than stepping from
    the previous, already-clamped date) keeps the day-of-month stable: a 31st
    schedule yields Jan 31, Feb 28, Mar 31, ... instead of drifting down to the
    28th after the first short month.
    """
    if frequency == ScheduleFrequency.WEEKLY:
        return start + timedelta(weeks=interval * n)
    if frequency == ScheduleFrequency.MONTHLY:
        return _add_months(start, interval * n)
    if frequency == ScheduleFrequency.YEARLY:
        return _add_months(start, 12 * interval * n)
    # DAILY and any unknown frequency fall back to day steps.
    return start + timedelta(days=interval * n)


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
    for n in range(max_occurrences):
        current = _occurrence(start, frequency, interval, n)
        if current > date_to:
            break
        if current >= date_from:
            result.append(current)
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
    for n in range(max_steps):
        current = _occurrence(start, frequency, interval, n)
        if end is not None and current > end:
            return None
        if current > after:
            return current
    return None

