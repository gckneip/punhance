"""Tests for schedule occurrence math (investment_schedule_service).

Pure date-stepping logic: occurrences_between lists occurrence dates in a window
(respecting the schedule's own end), and next_occurrence finds the first date
strictly after a cursor. Covers frequencies, intervals, month-end day clamping,
and window/end truncation.
"""

from datetime import date

from src.domain.entities.investment_schedule import ScheduleFrequency
from src.domain.services.investment_schedule_service import (
    occurrences_between,
    next_occurrence,
)

MONTHLY = ScheduleFrequency.MONTHLY
WEEKLY = ScheduleFrequency.WEEKLY
DAILY = ScheduleFrequency.DAILY
YEARLY = ScheduleFrequency.YEARLY


# --- occurrences_between --------------------------------------------------

def test_monthly_occurrences_in_window():
    occ = occurrences_between(
        MONTHLY, 1,
        start=date(2026, 1, 15),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
    )
    assert occ == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
        date(2026, 4, 15),
    ]


def test_date_from_excludes_earlier_occurrences():
    occ = occurrences_between(
        MONTHLY, 1,
        start=date(2026, 1, 15),
        date_from=date(2026, 3, 1),   # skip Jan/Feb
        date_to=date(2026, 4, 30),
    )
    assert occ == [date(2026, 3, 15), date(2026, 4, 15)]


def test_month_end_day_drifts_down_after_clamping():
    # Documents CURRENT behavior: stepping is cumulative (each step adds a month
    # to the *previous* occurrence), so once Jan 31 clamps to Feb 28 the day
    # never recovers -> Mar 28, Apr 28. A start-anchored stepper would instead
    # give Mar 31 / Apr 30. See the "month-end day drift" note flagged to the
    # team; update this expectation if that is fixed.
    occ = occurrences_between(
        MONTHLY, 1,
        start=date(2026, 1, 31),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
    )
    assert occ == [
        date(2026, 1, 31),
        date(2026, 2, 28),   # 2026 is not a leap year
        date(2026, 3, 28),   # drifted: NOT Mar 31
        date(2026, 4, 28),   # drifted: NOT Apr 30
    ]


def test_end_date_truncates_window():
    occ = occurrences_between(
        MONTHLY, 1,
        start=date(2026, 1, 10),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        end=date(2026, 3, 15),       # schedule ends mid-March
    )
    assert occ == [date(2026, 1, 10), date(2026, 2, 10), date(2026, 3, 10)]


def test_interval_greater_than_one():
    occ = occurrences_between(
        MONTHLY, 2,                  # every 2 months
        start=date(2026, 1, 1),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 6, 30),
    )
    assert occ == [date(2026, 1, 1), date(2026, 3, 1), date(2026, 5, 1)]


def test_weekly_daily_yearly_steps():
    weekly = occurrences_between(
        WEEKLY, 1, start=date(2026, 1, 1),
        date_from=date(2026, 1, 1), date_to=date(2026, 1, 22),
    )
    assert weekly == [date(2026, 1, 1), date(2026, 1, 8),
                      date(2026, 1, 15), date(2026, 1, 22)]

    daily = occurrences_between(
        DAILY, 1, start=date(2026, 1, 1),
        date_from=date(2026, 1, 1), date_to=date(2026, 1, 3),
    )
    assert daily == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    yearly = occurrences_between(
        YEARLY, 1, start=date(2024, 6, 1),
        date_from=date(2024, 1, 1), date_to=date(2026, 12, 31),
    )
    assert yearly == [date(2024, 6, 1), date(2025, 6, 1), date(2026, 6, 1)]


def test_interval_zero_is_coerced_to_one():
    occ = occurrences_between(
        DAILY, 0, start=date(2026, 1, 1),
        date_from=date(2026, 1, 1), date_to=date(2026, 1, 3),
    )
    assert occ == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]


# --- next_occurrence ------------------------------------------------------

def test_next_occurrence_is_strictly_after_cursor():
    nxt = next_occurrence(
        MONTHLY, 1, start=date(2026, 1, 15), after=date(2026, 2, 15)
    )
    # 2026-02-15 is an occurrence but `after` is exclusive -> March
    assert nxt == date(2026, 3, 15)


def test_next_occurrence_before_start_returns_start():
    nxt = next_occurrence(
        MONTHLY, 1, start=date(2026, 5, 1), after=date(2026, 1, 1)
    )
    assert nxt == date(2026, 5, 1)


def test_next_occurrence_past_end_returns_none():
    nxt = next_occurrence(
        MONTHLY, 1, start=date(2026, 1, 15),
        after=date(2026, 3, 20), end=date(2026, 3, 31),
    )
    assert nxt is None
