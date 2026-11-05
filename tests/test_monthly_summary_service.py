"""Tests for MonthlySummaryService income/expense totals for a calendar month."""
from datetime import date

from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.services.monthly_summary_service import MonthlySummaryService
from tests._fakes import FakeEventRepo, FakeCategoryRepo


def _ev(event_type, amount, on=date(2026, 5, 10), **kwargs):
    return FinancialEvent(
        event_type=event_type, event_date=on, description="t", amount=amount, **kwargs
    )


def _service(events, investment_cats=()):
    return MonthlySummaryService(FakeEventRepo(events), FakeCategoryRepo(investment_cats))


def test_income_sums_income_and_refund():
    svc = _service([
        _ev(EventType.INCOME, 100.0),
        _ev(EventType.REFUND, 25.0),
    ])
    s = svc.get_summary(2026, 5)
    assert s.income == 125.0
    assert s.expenses == 0.0
    assert s.net == 125.0


def test_expenses_sum_expense_purchase_cardpayment_loan():
    svc = _service([
        _ev(EventType.EXPENSE, 10.0),
        _ev(EventType.PURCHASE, 20.0),
        _ev(EventType.CARD_PAYMENT, 30.0),
        _ev(EventType.LOAN_PAYMENT, 40.0),
    ])
    s = svc.get_summary(2026, 5)
    assert s.expenses == 100.0
    assert s.net == -100.0


def test_transfer_investment_redemption_are_excluded():
    svc = _service([
        _ev(EventType.TRANSFER, 500.0),
        _ev(EventType.INVESTMENT, 300.0),
        _ev(EventType.REDEMPTION, 200.0),
    ])
    s = svc.get_summary(2026, 5)
    assert s.income == 0.0
    assert s.expenses == 0.0


def test_investment_category_events_excluded():
    svc = _service(
        [
            _ev(EventType.INCOME, 100.0, category_id="invcat"),
            _ev(EventType.EXPENSE, 40.0, category_id="invcat"),
            _ev(EventType.EXPENSE, 10.0, category_id="normal"),
        ],
        investment_cats=["invcat"],
    )
    s = svc.get_summary(2026, 5)
    assert s.income == 0.0
    assert s.expenses == 10.0


def test_uncleared_card_charge_is_skipped():
    # An expense charged to a card whose bill is still open must not count
    # (it is counted later as the CARD_PAYMENT that settles the bill).
    svc = _service([
        _ev(EventType.EXPENSE, 40.0, credit_card_id="card1"),
        _ev(EventType.EXPENSE, 10.0),  # cash expense, counts
    ])
    s = svc.get_summary(2026, 5)
    assert s.expenses == 10.0


def test_events_outside_the_month_are_excluded():
    svc = _service([
        _ev(EventType.INCOME, 100.0, on=date(2026, 5, 31)),
        _ev(EventType.INCOME, 999.0, on=date(2026, 6, 1)),   # next month
        _ev(EventType.INCOME, 777.0, on=date(2026, 4, 30)),  # prev month
    ])
    s = svc.get_summary(2026, 5)
    assert s.income == 100.0


def test_december_rolls_over_to_next_year():
    svc = _service([
        _ev(EventType.INCOME, 100.0, on=date(2026, 12, 15)),
        _ev(EventType.INCOME, 999.0, on=date(2027, 1, 1)),   # excluded
    ])
    s = svc.get_summary(2026, 12)
    assert s.income == 100.0
