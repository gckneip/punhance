"""Tests for AccountSummaryService balance/income/expense reconciliation.

Focus on the investment-feature behavior: investment and redemption movements
(and investment-flagged categories) move an account's balance but are kept out
of income/expense totals, exactly like internal transfers.
"""
from datetime import date

import pytest

from src.domain.entities.account import Account, AccountType
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.services.account_summary_service import AccountSummaryService
from tests._fakes import FakeEventRepo, FakeAccountRepo, FakeCategoryRepo


def _acc(name, initial=0.0, type_=AccountType.CHECKING):
    return Account(name=name, type=type_, initial_balance=initial)


def _ev(event_type, amount, account_id=None, **kwargs):
    return FinancialEvent(
        event_type=event_type,
        event_date=date(2026, 5, 10),
        description="t",
        amount=amount,
        account_id=account_id,
        **kwargs,
    )


def _service(accounts, events, investment_cats=()):
    return AccountSummaryService(
        FakeEventRepo(events),
        FakeAccountRepo(accounts),
        FakeCategoryRepo(investment_cats),
    )


def _item(summary, account_id):
    return next(i for i in summary.items if i.account_id == account_id)


# --- basic income / expense ----------------------------------------------

def test_income_and_expense_move_balance():
    a = _acc("Checking", initial=100.0)
    svc = _service([a], [
        _ev(EventType.INCOME, 50.0, a.id),
        _ev(EventType.EXPENSE, 30.0, a.id),
    ])
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.total_income == 50.0
    assert item.total_expenses == 30.0
    assert item.current_balance == 120.0       # 100 + 50 - 30
    assert s.grand_total == 120.0


def test_credit_card_expense_is_not_an_account_outflow():
    a = _acc("Checking", initial=100.0)
    svc = _service([a], [
        _ev(EventType.EXPENSE, 40.0, a.id, credit_card_id="card1"),
    ])
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.total_expenses == 0.0          # charged to the card, not the account
    assert item.current_balance == 100.0


def test_card_payment_is_an_expense_against_the_account():
    a = _acc("Checking", initial=100.0)
    svc = _service([a], [_ev(EventType.CARD_PAYMENT, 40.0, a.id)])
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.total_expenses == 40.0
    assert item.current_balance == 60.0


# --- transfers ------------------------------------------------------------

def test_transfer_moves_balance_but_is_not_income_or_expense():
    src = _acc("Src", initial=100.0)
    dst = _acc("Dst", initial=0.0)
    ev = _ev(EventType.TRANSFER, 40.0, src.id)
    ev.destination_account_id = dst.id
    svc = _service([src, dst], [ev])
    s = svc.get_summary()
    si, di = _item(s, src.id), _item(s, dst.id)
    assert si.transfer_out == 40.0 and si.current_balance == 60.0
    assert di.transfer_in == 40.0 and di.current_balance == 40.0
    assert s.total_income == 0.0 and s.total_expenses == 0.0
    assert s.grand_total == 100.0              # transfers net to zero


# --- investment / redemption movements -----------------------------------

def test_investment_lowers_balance_as_a_transfer_out():
    a = _acc("Checking", initial=100.0)
    svc = _service([a], [_ev(EventType.INVESTMENT, 30.0, a.id)])
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.transfer_out == 30.0
    assert item.total_expenses == 0.0          # not spending
    assert item.current_balance == 70.0


def test_redemption_raises_balance_as_a_transfer_in():
    a = _acc("Checking", initial=100.0)
    svc = _service([a], [_ev(EventType.REDEMPTION, 25.0, a.id)])
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.transfer_in == 25.0
    assert item.total_income == 0.0            # not income
    assert item.current_balance == 125.0


# --- investment-flagged categories ---------------------------------------

def test_investment_category_expense_is_balance_only():
    a = _acc("Checking", initial=100.0)
    svc = _service(
        [a],
        [_ev(EventType.EXPENSE, 30.0, a.id, category_id="invcat")],
        investment_cats=["invcat"],
    )
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.total_expenses == 0.0
    assert item.transfer_out == 30.0
    assert item.current_balance == 70.0


def test_investment_category_income_is_balance_only():
    a = _acc("Checking", initial=100.0)
    svc = _service(
        [a],
        [_ev(EventType.INCOME, 20.0, a.id, category_id="invcat")],
        investment_cats=["invcat"],
    )
    s = svc.get_summary()
    item = _item(s, a.id)
    assert item.total_income == 0.0
    assert item.transfer_in == 20.0
    assert item.current_balance == 120.0


# --- unassigned bucket ----------------------------------------------------

def test_events_without_account_fall_into_unassigned_bucket():
    a = _acc("Checking", initial=100.0)
    svc = _service([a], [_ev(EventType.INCOME, 15.0, account_id=None)])
    s = svc.get_summary()
    unassigned = _item(s, "__unassigned__")
    assert unassigned.total_income == 15.0
    assert s.total_income == 15.0
    assert s.grand_total == 115.0              # 100 initial + 15 unassigned income
