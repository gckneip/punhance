"""Tests for CreditCardService.get_status: rolling installment charges,
directly-tagged expense events, and card payments into a current-debt and
available-credit figure.
"""
from datetime import date

from src.domain.entities.credit_card import CreditCard
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.entities.installment import Installment, InstallmentStatus
from src.domain.services.credit_card_service import CreditCardService
from src.domain.services.installment_service import InstallmentService
from tests._fakes import FakeEventRepo, FakeInstallmentRepo


def _card(limit=1000.0):
    return CreditCard(
        name="Visa", issuer="Bank", credit_limit=limit, closing_day=1, due_day=10,
    )


def _inst(amount, plan="plan"):
    return Installment(plan, 1, amount, date(2026, 1, 1), InstallmentStatus.PENDING)


def _ev(event_type, amount, credit_card_id=None):
    return FinancialEvent(
        event_type=event_type,
        event_date=date(2026, 5, 10),
        description="t",
        amount=amount,
        credit_card_id=credit_card_id,
    )


def _service(card, installments=(), events=()):
    return CreditCardService(
        FakeInstallmentRepo({card.id: list(installments)}),
        InstallmentService(),
        FakeEventRepo(events),
    )


# --- installment-only debt ------------------------------------------------

def test_debt_from_installments_and_available_credit():
    card = _card(limit=1000.0)
    svc = _service(card, installments=[_inst(200.0), _inst(100.0)])
    status = svc.get_status(card)
    assert status.current_debt == 300.0
    assert status.available_credit == 700.0
    assert status.card is card


def test_no_installments_means_full_credit_available():
    card = _card(limit=500.0)
    svc = _service(card)
    status = svc.get_status(card)
    assert status.current_debt == 0
    assert status.available_credit == 500.0


# --- directly-tagged expense events --------------------------------------

def test_expense_tagged_to_card_adds_to_debt():
    card = _card(limit=1000.0)
    svc = _service(
        card,
        installments=[_inst(100.0)],
        events=[_ev(EventType.EXPENSE, 50.0, credit_card_id=card.id)],
    )
    status = svc.get_status(card)
    assert status.current_debt == 150.0
    assert status.available_credit == 850.0


def test_card_payment_reduces_debt():
    card = _card(limit=1000.0)
    svc = _service(
        card,
        installments=[_inst(300.0)],
        events=[_ev(EventType.CARD_PAYMENT, 120.0, credit_card_id=card.id)],
    )
    status = svc.get_status(card)
    assert status.current_debt == 180.0
    assert status.available_credit == 820.0


def test_expense_and_payment_net_out_with_installments():
    card = _card(limit=1000.0)
    svc = _service(
        card,
        installments=[_inst(200.0)],
        events=[
            _ev(EventType.EXPENSE, 100.0, credit_card_id=card.id),
            _ev(EventType.CARD_PAYMENT, 150.0, credit_card_id=card.id),
        ],
    )
    status = svc.get_status(card)
    assert status.current_debt == 150.0        # 200 + 100 - 150


def test_available_credit_can_go_negative_when_over_limit():
    card = _card(limit=100.0)
    svc = _service(card, installments=[_inst(250.0)])
    status = svc.get_status(card)
    assert status.current_debt == 250.0
    assert status.available_credit == -150.0


# --- optional event repository -------------------------------------------

def test_works_without_event_repository():
    # The event repo is optional; without it, only installments count.
    card = _card(limit=1000.0)
    svc = CreditCardService(
        FakeInstallmentRepo({card.id: [_inst(400.0)]}),
        InstallmentService(),
    )
    status = svc.get_status(card)
    assert status.current_debt == 400.0
    assert status.available_credit == 600.0
