"""Tests for CategoryBreakdownService grouping, exclusions, and purchase splits."""
from datetime import date
from types import SimpleNamespace

from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from tests._fakes import FakeEventRepo, FakeCategoryRepo, FakePurchaseRepo


def _ev(event_type, amount, category_id=None, on=date(2026, 5, 10), **kwargs):
    return FinancialEvent(
        event_type=event_type, event_date=on, description="t",
        amount=amount, category_id=category_id, **kwargs,
    )


def _service(events, investment_cats=(), purchase_repo=None):
    return CategoryBreakdownService(
        FakeEventRepo(events),
        purchase_repository=purchase_repo,
        category_repository=FakeCategoryRepo(investment_cats),
    )


def _by_cat(breakdown):
    return {i.category_id: i for i in breakdown.items}


def test_groups_income_and_expense_by_category():
    svc = _service([
        _ev(EventType.INCOME, 100.0, "salary"),
        _ev(EventType.EXPENSE, 30.0, "food"),
        _ev(EventType.EXPENSE, 20.0, "food"),
    ])
    items = _by_cat(svc.get_breakdown(2026, 5))
    assert items["salary"].total_income == 100.0
    assert items["food"].total_expenses == 50.0
    assert items["food"].event_count == 2
    assert items["food"].net == -50.0


def test_investment_categories_are_excluded():
    svc = _service(
        [
            _ev(EventType.EXPENSE, 40.0, "invcat"),
            _ev(EventType.EXPENSE, 10.0, "food"),
        ],
        investment_cats=["invcat"],
    )
    items = _by_cat(svc.get_breakdown(2026, 5))
    assert "invcat" not in items
    assert items["food"].total_expenses == 10.0


def test_transfer_cardpayment_investment_redemption_excluded():
    svc = _service([
        _ev(EventType.TRANSFER, 500.0, "x"),
        _ev(EventType.CARD_PAYMENT, 400.0, "x"),
        _ev(EventType.INVESTMENT, 300.0, "x"),
        _ev(EventType.REDEMPTION, 200.0, "x"),
        _ev(EventType.EXPENSE, 10.0, "food"),
    ])
    b = svc.get_breakdown(2026, 5)
    items = _by_cat(b)
    assert set(items) == {"food"}
    assert b.total_expenses == 10.0


def test_purchase_is_split_across_item_categories():
    purchase_event = _ev(EventType.PURCHASE, 100.0, category_id=None)
    purchase = SimpleNamespace(id="p1")
    items = [
        SimpleNamespace(category_id="food", total_price=70.0),
        SimpleNamespace(category_id="cleaning", total_price=30.0),
    ]
    repo = FakePurchaseRepo(
        by_event={purchase_event.id: purchase},
        items_by_purchase={"p1": items},
    )
    svc = _service([purchase_event], purchase_repo=repo)
    by = _by_cat(svc.get_breakdown(2026, 5))
    assert by["food"].total_expenses == 70.0
    assert by["cleaning"].total_expenses == 30.0


def test_category_id_filter_returns_only_that_category():
    svc = _service([
        _ev(EventType.EXPENSE, 30.0, "food"),
        _ev(EventType.EXPENSE, 20.0, "transport"),
    ])
    b = svc.get_breakdown(2026, 5, category_id="food")
    assert [i.category_id for i in b.items] == ["food"]
    assert b.total_expenses == 30.0


def test_items_sorted_by_expenses_desc():
    svc = _service([
        _ev(EventType.EXPENSE, 10.0, "small"),
        _ev(EventType.EXPENSE, 90.0, "big"),
        _ev(EventType.EXPENSE, 50.0, "mid"),
    ])
    b = svc.get_breakdown(2026, 5)
    assert [i.category_id for i in b.items] == ["big", "mid", "small"]


def test_get_events_for_category_lists_contributing_events():
    svc = _service([
        _ev(EventType.EXPENSE, 30.0, "food", on=date(2026, 5, 2)),
        _ev(EventType.EXPENSE, 20.0, "food", on=date(2026, 5, 20)),
        _ev(EventType.EXPENSE, 99.0, "other"),
        _ev(EventType.INVESTMENT, 500.0, "food"),  # excluded type
    ])
    rows = svc.get_events_for_category(date(2026, 5, 1), date(2026, 6, 1), "food")
    assert [r.amount for r in rows] == [20.0, 30.0]   # sorted most-recent first
    assert all(not r.is_income for r in rows)
