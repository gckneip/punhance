"""Tests for RecurringEventService occurrence generation.

Window semantics under test: date_from is inclusive, date_to is exclusive,
and a rule's end_date is inclusive. Covers all four frequencies, intervals,
day/weekday/month anchoring, short-month clamping, and the pending-occurrence
exclusion of already-confirmed or skipped dates.
"""
from datetime import date

import pytest

from src.domain.entities.financial_event import EventType
from src.domain.entities.recurring_event import RecurrenceFrequency, RecurringEvent
from src.domain.services.recurring_event_service import RecurringEventService


def _rule(frequency, start, **kwargs):
    return RecurringEvent(
        event_type=EventType.EXPENSE,
        description="rent",
        amount=10.0,
        frequency=frequency,
        start_date=start,
        **kwargs,
    )


@pytest.fixture
def svc():
    return RecurringEventService()


# --- daily ----------------------------------------------------------------

def test_daily_every_day(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1))
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 1, 5))
    assert occ == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3), date(2026, 1, 4)]


def test_daily_with_interval(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1), interval=3)
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 1, 11))
    assert occ == [date(2026, 1, 1), date(2026, 1, 4), date(2026, 1, 7), date(2026, 1, 10)]


# --- weekly ---------------------------------------------------------------

def test_weekly_defaults_to_start_dates_weekday(svc):
    # 2026-01-01 is a Thursday.
    rule = _rule(RecurrenceFrequency.WEEKLY, date(2026, 1, 1))
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 1, 23))
    assert occ == [date(2026, 1, 1), date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 22)]


def test_weekly_anchors_to_explicit_weekday(svc):
    # Start Thu 2026-01-01, but anchor to Monday (weekday=0): first Mon is 01-05.
    rule = _rule(RecurrenceFrequency.WEEKLY, date(2026, 1, 1), weekday=0)
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 1, 20))
    assert occ == [date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19)]


def test_weekly_with_interval(svc):
    rule = _rule(RecurrenceFrequency.WEEKLY, date(2026, 1, 1), interval=2)
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 2, 1))
    assert occ == [date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 29)]


# --- monthly --------------------------------------------------------------

def test_monthly_same_day_each_month(svc):
    rule = _rule(RecurrenceFrequency.MONTHLY, date(2026, 1, 15))
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 1))
    assert occ == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]


def test_monthly_clamps_to_short_months(svc):
    # day_of_month 31 falls back to the last day of shorter months, and the
    # clamp must not bleed forward (March is still the 31st).
    rule = _rule(RecurrenceFrequency.MONTHLY, date(2026, 1, 31))
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 1))
    assert occ == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_monthly_explicit_day_of_month(svc):
    rule = _rule(RecurrenceFrequency.MONTHLY, date(2026, 1, 1), day_of_month=10)
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 3, 1))
    assert occ == [date(2026, 1, 10), date(2026, 2, 10)]


def test_monthly_with_interval_crosses_year(svc):
    rule = _rule(RecurrenceFrequency.MONTHLY, date(2026, 11, 5), interval=2)
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2027, 4, 1))
    assert occ == [date(2026, 11, 5), date(2027, 1, 5), date(2027, 3, 5)]


# --- yearly ---------------------------------------------------------------

def test_yearly_same_date_each_year(svc):
    rule = _rule(RecurrenceFrequency.YEARLY, date(2026, 6, 20))
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2029, 1, 1))
    assert occ == [date(2026, 6, 20), date(2027, 6, 20), date(2028, 6, 20)]


def test_yearly_clamps_leap_day(svc):
    # Feb 29 only exists on leap years; other years clamp to Feb 28.
    rule = _rule(RecurrenceFrequency.YEARLY, date(2024, 2, 29))
    occ = svc.generate_occurrences(rule, date(2024, 1, 1), date(2027, 1, 1))
    assert occ == [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28)]


# --- window + end_date ----------------------------------------------------

def test_date_from_is_inclusive_date_to_is_exclusive(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1))
    occ = svc.generate_occurrences(rule, date(2026, 1, 2), date(2026, 1, 4))
    assert occ == [date(2026, 1, 2), date(2026, 1, 3)]


def test_end_date_is_inclusive(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1), end_date=date(2026, 1, 3))
    occ = svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 1, 31))
    assert occ == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]


def test_occurrences_before_window_are_skipped(svc):
    rule = _rule(RecurrenceFrequency.MONTHLY, date(2026, 1, 15))
    occ = svc.generate_occurrences(rule, date(2026, 3, 1), date(2026, 5, 1))
    assert occ == [date(2026, 3, 15), date(2026, 4, 15)]


# --- guards ---------------------------------------------------------------

def test_inactive_rule_yields_nothing(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1), is_active=False)
    assert svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 2, 1)) == []


def test_non_positive_interval_yields_nothing(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1), interval=0)
    assert svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 2, 1)) == []


def test_empty_window_yields_nothing(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1))
    assert svc.generate_occurrences(rule, date(2026, 1, 5), date(2026, 1, 5)) == []


# --- pending occurrences --------------------------------------------------

def test_pending_excludes_confirmed_and_skipped(svc):
    rule = _rule(RecurrenceFrequency.DAILY, date(2026, 1, 1))
    pending = svc.compute_pending_occurrences(
        rule,
        date(2026, 1, 1),
        date(2026, 1, 6),
        confirmed_dates=[date(2026, 1, 2)],
        skipped_dates=[date(2026, 1, 4)],
    )
    assert pending == [date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 5)]


def test_pending_with_nothing_excluded_matches_generate(svc):
    rule = _rule(RecurrenceFrequency.WEEKLY, date(2026, 1, 1))
    window = (date(2026, 1, 1), date(2026, 2, 1))
    pending = svc.compute_pending_occurrences(rule, *window, confirmed_dates=[], skipped_dates=[])
    assert pending == svc.generate_occurrences(rule, *window)
