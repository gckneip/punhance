"""Tests for the grocery shopping-suggestion engine.

These exercise the service through the real SQLite repository (against an
in-memory database) so the new ``find_product_purchase_history`` join is
covered alongside the recurrence logic.
"""

import sqlite3
import uuid
from datetime import date

import pytest

from src.infrastructure.database.schema import create_tables
from src.infrastructure.repositories.sqlite_purchase_repository import (
    SQLitePurchaseRepository,
)
from src.domain.services.shopping_suggestion_service import ShoppingSuggestionService


# --- fixtures / helpers ---------------------------------------------------

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    create_tables(c)
    return c


@pytest.fixture
def service(conn):
    return ShoppingSuggestionService(SQLitePurchaseRepository(conn))


def _add_product(conn, name):
    pid = str(uuid.uuid4())
    conn.execute("INSERT INTO products (id, name) VALUES (?, ?)", (pid, name))
    return pid


def _add_counterparty(conn, name):
    cid = str(uuid.uuid4())
    conn.execute("INSERT INTO counterparties (id, name) VALUES (?, ?)", (cid, name))
    return cid


def _add_purchase(conn, on_date, items, counterparty_id=None):
    """items: list of (product_id, quantity, unit, unit_price)."""
    event_id = str(uuid.uuid4())
    purchase_id = str(uuid.uuid4())
    total = sum(q * p for _, q, _, p in items)
    conn.execute(
        """INSERT INTO financial_events
           (id, event_type, event_date, description, amount, currency, counterparty_id)
           VALUES (?, 'PURCHASE', ?, 'test', ?, 'BRL', ?)""",
        (event_id, on_date.isoformat(), total, counterparty_id),
    )
    conn.execute(
        """INSERT INTO purchases
           (id, financial_event_id, total_amount, payment_method, counterparty_id, invoice_date)
           VALUES (?, ?, ?, 'CASH', ?, ?)""",
        (purchase_id, event_id, total, counterparty_id, on_date.isoformat()),
    )
    for product_id, qty, unit, unit_price in items:
        conn.execute(
            """INSERT INTO purchase_items
               (id, purchase_id, name, quantity, unit, unit_price, total_price, product_id)
               VALUES (?, ?, 'item', ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), purchase_id, qty, unit, unit_price,
             qty * unit_price, product_id),
        )
    conn.commit()
    return purchase_id


def _by_product(shopping_list):
    return {s.product_id: s for s in shopping_list.items}


# --- tests ----------------------------------------------------------------

def test_empty_history_yields_empty_list(service):
    result = service.suggest("monthly", reference_date=date(2026, 10, 1))
    assert result.items == []
    assert result.total_estimated_cost == 0.0


def test_unknown_horizon_raises(service):
    with pytest.raises(ValueError):
        service.suggest("yearly")


def test_single_purchase_is_not_suggested(conn, service):
    rice = _add_product(conn, "rice")
    _add_purchase(conn, date(2026, 9, 1), [(rice, 5, "KG", 6.0)])
    result = service.suggest("monthly", reference_date=date(2026, 10, 1))
    assert rice not in _by_product(result)


def test_regular_monthly_product_is_predicted(conn, service):
    rice = _add_product(conn, "rice")
    # Bought on the 1st of three consecutive months: interval = ~30 days.
    _add_purchase(conn, date(2026, 7, 1), [(rice, 5, "KG", 6.0)])
    _add_purchase(conn, date(2026, 8, 1), [(rice, 5, "KG", 6.0)])
    _add_purchase(conn, date(2026, 9, 1), [(rice, 5, "KG", 7.0)])

    result = service.suggest("monthly", reference_date=date(2026, 9, 20))
    s = _by_product(result)[rice]

    assert s.occurrences == 3
    assert s.avg_interval_days == 31          # median of [31, 31]
    assert s.typical_quantity == 5
    assert s.unit == "KG"
    assert s.last_purchase_date == date(2026, 9, 1)
    assert s.predicted_next_date == date(2026, 10, 2)  # 2026-09-01 + 31d
    # due 2026-10-02, ref 2026-09-20 -> 12 days out
    assert s.days_until_due == 12
    # most recent unit price (7.0) drives the estimate, not the earlier 6.0
    assert s.estimated_unit_price == 7.0
    assert s.estimated_cost == 35.0


def test_weekly_horizon_excludes_far_off_but_includes_soon_due(conn, service):
    # Monthly item last bought long enough ago that it is due in ~5 days.
    rice = _add_product(conn, "rice")
    _add_purchase(conn, date(2026, 8, 6), [(rice, 1, "KG", 6.0)])
    _add_purchase(conn, date(2026, 9, 5), [(rice, 1, "KG", 6.0)])  # +30d
    # Monthly item just bought -> next due ~30 days out, outside a weekly window.
    oil = _add_product(conn, "oil")
    _add_purchase(conn, date(2026, 8, 1), [(oil, 1, "UNIT", 9.0)])
    _add_purchase(conn, date(2026, 9, 28), [(oil, 1, "UNIT", 9.0)])

    ref = date(2026, 10, 1)
    weekly = _by_product(service.suggest("weekly", reference_date=ref))
    monthly = _by_product(service.suggest("monthly", reference_date=ref))

    # rice predicted 2026-09-05 + 30d = 2026-10-05 -> 4 days out: in weekly
    assert rice in weekly
    # oil predicted 2026-09-28 + 58d -> far out: not in weekly, but may be monthly-less too
    assert oil not in weekly
    # both are visible on a wider lens only if due within 30 days
    assert rice in monthly


def test_overdue_item_sorts_first_and_has_negative_days(conn, service):
    rice = _add_product(conn, "rice")
    milk = _add_product(conn, "milk")
    # rice: weekly cadence, last bought 20 days ago -> very overdue
    _add_purchase(conn, date(2026, 8, 25), [(rice, 1, "KG", 6.0)])
    _add_purchase(conn, date(2026, 9, 1), [(rice, 1, "KG", 6.0)])   # interval 7d
    # milk: monthly cadence, due right around the reference date
    _add_purchase(conn, date(2026, 8, 2), [(milk, 2, "UNIT", 4.0)])
    _add_purchase(conn, date(2026, 9, 1), [(milk, 2, "UNIT", 4.0)])  # +30d

    result = service.suggest("monthly", reference_date=date(2026, 10, 1))
    rice_s = _by_product(result)[rice]
    assert rice_s.days_until_due < 0                 # overdue
    assert result.items[0].product_id == rice        # sorted most-overdue first


def test_same_day_line_items_collapse_into_one_trip(conn, service):
    rice = _add_product(conn, "rice")
    # Two line items of the same product in one trip -> quantities add up, and
    # it still counts as a single occurrence, not two.
    _add_purchase(conn, date(2026, 8, 1), [(rice, 2, "KG", 6.0), (rice, 3, "KG", 6.0)])
    _add_purchase(conn, date(2026, 9, 1), [(rice, 5, "KG", 6.0)])

    s = _by_product(service.suggest("monthly", reference_date=date(2026, 9, 20)))[rice]
    assert s.occurrences == 2
    assert s.typical_quantity == 5  # median of [5, 5]


def test_cheapest_store_is_reported(conn, service):
    rice = _add_product(conn, "rice")
    cheap = _add_counterparty(conn, "Cheap Mart")
    pricey = _add_counterparty(conn, "Pricey Place")
    _add_purchase(conn, date(2026, 8, 1), [(rice, 1, "KG", 8.0)], counterparty_id=pricey)
    _add_purchase(conn, date(2026, 9, 1), [(rice, 1, "KG", 5.0)], counterparty_id=cheap)

    s = _by_product(service.suggest("monthly", reference_date=date(2026, 9, 20)))[rice]
    assert s.cheapest_counterparty_id == cheap
    assert s.cheapest_unit_price == 5.0


def test_confidence_high_for_regular_cadence(conn, service):
    rice = _add_product(conn, "rice")
    for m in (5, 6, 7, 8, 9):
        _add_purchase(conn, date(2026, m, 1), [(rice, 1, "KG", 6.0)])
    s = _by_product(service.suggest("monthly", reference_date=date(2026, 9, 25)))[rice]
    assert s.occurrences == 5
    assert s.confidence == "high"


def test_total_estimated_cost_sums_items(conn, service):
    rice = _add_product(conn, "rice")
    milk = _add_product(conn, "milk")
    _add_purchase(conn, date(2026, 8, 1), [(rice, 5, "KG", 6.0), (milk, 2, "UNIT", 4.0)])
    _add_purchase(conn, date(2026, 9, 1), [(rice, 5, "KG", 6.0), (milk, 2, "UNIT", 4.0)])

    result = service.suggest("monthly", reference_date=date(2026, 9, 25))
    expected = sum(s.estimated_cost for s in result.items)
    assert result.total_estimated_cost == round(expected, 2)
    assert result.total_estimated_cost == 38.0  # 5*6 + 2*4
