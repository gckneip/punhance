"""Tests for InstallmentService: splitting a plan into dated installments
and summing installment charges into credit-card debt.

Focus on the rounding/remainder placement and the month-rollover logic that
turns a first due date into one Installment per month.
"""
from datetime import date

from src.domain.entities.installment import Installment, InstallmentStatus
from src.domain.entities.installment_plan import InstallmentPlan
from src.domain.services.installment_service import InstallmentService


def _plan(total, count, remainder_on_first=False):
    return InstallmentPlan(
        purchase_id="p1",
        total_amount=total,
        installment_count=count,
        remainder_on_first=remainder_on_first,
    )


# --- splitting / rounding -------------------------------------------------

def test_even_split_sums_to_total():
    svc = InstallmentService()
    inst = svc.create_installments(_plan(300.0, 3), date(2026, 1, 10))
    assert len(inst) == 3
    assert [i.amount for i in inst] == [100.0, 100.0, 100.0]
    assert round(sum(i.amount for i in inst), 2) == 300.0


def test_remainder_goes_on_last_installment_by_default():
    # 100 / 3 = 33.33 each, remainder 0.01 lands on the last one.
    svc = InstallmentService()
    inst = svc.create_installments(_plan(100.0, 3), date(2026, 1, 10))
    assert [i.amount for i in inst] == [33.33, 33.33, 33.34]
    assert round(sum(i.amount for i in inst), 2) == 100.0


def test_remainder_on_first_when_flagged():
    svc = InstallmentService()
    inst = svc.create_installments(_plan(100.0, 3, remainder_on_first=True), date(2026, 1, 10))
    assert [i.amount for i in inst] == [33.34, 33.33, 33.33]
    assert round(sum(i.amount for i in inst), 2) == 100.0


def test_installments_are_numbered_and_pending():
    svc = InstallmentService()
    plan = _plan(200.0, 4)
    inst = svc.create_installments(plan, date(2026, 1, 10))
    assert [i.installment_number for i in inst] == [1, 2, 3, 4]
    assert all(i.status is InstallmentStatus.PENDING for i in inst)
    assert all(i.installment_plan_id == plan.id for i in inst)


# --- due-date rollover ----------------------------------------------------

def test_due_dates_advance_one_month_each():
    svc = InstallmentService()
    inst = svc.create_installments(_plan(300.0, 3), date(2026, 1, 10))
    assert [i.due_date for i in inst] == [
        date(2026, 1, 10), date(2026, 2, 10), date(2026, 3, 10),
    ]


def test_due_dates_roll_across_year_boundary():
    svc = InstallmentService()
    inst = svc.create_installments(_plan(300.0, 3), date(2026, 11, 15))
    assert [i.due_date for i in inst] == [
        date(2026, 11, 15), date(2026, 12, 15), date(2027, 1, 15),
    ]


def test_due_day_clamps_to_short_months():
    # Jan 31 -> Feb has no 31st, clamp to the 28th (2026 is not a leap year).
    svc = InstallmentService()
    inst = svc.create_installments(_plan(200.0, 2), date(2026, 1, 31))
    assert [i.due_date for i in inst] == [date(2026, 1, 31), date(2026, 2, 28)]


def test_due_day_clamp_does_not_bleed_into_later_months():
    # Clamping Feb back to the 28th must not shrink March — it stays the 31st.
    svc = InstallmentService()
    inst = svc.create_installments(_plan(300.0, 3), date(2026, 1, 31))
    assert [i.due_date for i in inst] == [
        date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
    ]


# --- debt aggregation -----------------------------------------------------

def test_credit_card_debt_sums_all_installments_regardless_of_status():
    svc = InstallmentService()
    installments = [
        Installment("plan", 1, 50.0, date(2026, 1, 1), InstallmentStatus.PAID),
        Installment("plan", 2, 50.0, date(2026, 2, 1), InstallmentStatus.PENDING),
        Installment("plan", 3, 25.0, date(2026, 3, 1), InstallmentStatus.OVERDUE),
    ]
    assert svc.get_credit_card_debt(installments) == 125.0


def test_credit_card_debt_of_no_installments_is_zero():
    assert InstallmentService().get_credit_card_debt([]) == 0
