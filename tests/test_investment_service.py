"""Tests for the position/portfolio math in InvestmentService.

Pure-logic unit tests: they build Investment and InvestmentTransaction objects
directly (no repository/DB needed) and assert the weighted-average cost math,
income accounting, amount-based-holding handling, and portfolio aggregation.
"""

import pytest

from src.domain.entities.investment import Investment, AssetType
from src.domain.entities.investment_transaction import (
    InvestmentTransaction,
    InvestmentTxnType,
)
from src.domain.services.investment_service import InvestmentService


# --- fixtures / helpers ---------------------------------------------------

@pytest.fixture
def service():
    return InvestmentService()


def _holding(asset_type=AssetType.RENDA_VARIAVEL_BR, current_price=0.0, **kwargs):
    return Investment(
        name="Test", asset_type=asset_type, current_price=current_price, **kwargs
    )


def _txn(txn_type, quantity=0.0, total=0.0, unit_price=0.0):
    return InvestmentTransaction(
        investment_id="x",
        txn_type=txn_type,
        date="2026-01-01",
        quantity=quantity,
        unit_price=unit_price,
        total=total,
    )


# --- empty / degenerate positions ----------------------------------------

def test_no_transactions_yields_zero_position(service):
    pos = service.compute_position(_holding(current_price=10.0), [])
    assert pos.quantity == 0.0
    assert pos.net_invested == 0.0
    assert pos.avg_unit_price == 0.0
    # amount-based fallback: quantity 0 is treated as 1, so market value == price
    assert pos.market_value == 10.0
    assert pos.income_total == 0.0
    assert pos.return_pct == 0.0  # guarded: net_invested <= 0


# --- principal in: quantity, invested, average cost -----------------------

def test_single_buy_sets_quantity_and_invested(service):
    inv = _holding(current_price=5.0)
    pos = service.compute_position(inv, [_txn(InvestmentTxnType.BUY, quantity=10, total=20.0)])
    assert pos.quantity == 10.0
    assert pos.net_invested == 20.0
    assert pos.avg_unit_price == 2.0
    assert pos.market_value == 50.0            # 5.0 * 10
    assert pos.unrealized_gain == 30.0         # 50 - 20
    assert pos.total_return == 30.0
    assert pos.return_pct == pytest.approx(150.0)  # 30 / 20 * 100


def test_multiple_buys_use_weighted_average_cost(service):
    inv = _holding(current_price=5.0)
    pos = service.compute_position(inv, [
        _txn(InvestmentTxnType.BUY, quantity=10, total=20.0),   # @2.0
        _txn(InvestmentTxnType.CONTRIBUTION, quantity=10, total=40.0),  # @4.0
    ])
    assert pos.quantity == 20.0
    assert pos.net_invested == 60.0
    assert pos.avg_unit_price == pytest.approx(3.0)  # 60 / 20


def test_sell_reduces_quantity_and_invested(service):
    inv = _holding(current_price=5.0)
    pos = service.compute_position(inv, [
        _txn(InvestmentTxnType.BUY, quantity=10, total=20.0),
        _txn(InvestmentTxnType.SELL, quantity=4, total=12.0),  # proceeds reduce basis
    ])
    assert pos.quantity == 6.0
    assert pos.net_invested == 8.0             # 20 - 12
    assert pos.market_value == 30.0            # 5.0 * 6


# --- income vs cost types -------------------------------------------------

def test_income_and_cost_types_affect_only_income(service):
    inv = _holding(current_price=5.0)
    pos = service.compute_position(inv, [
        _txn(InvestmentTxnType.BUY, quantity=10, total=20.0),
        _txn(InvestmentTxnType.DIVIDEND, total=50.0),
        _txn(InvestmentTxnType.INTEREST, total=5.0),
        _txn(InvestmentTxnType.FEE, total=10.0),
        _txn(InvestmentTxnType.TAX, total=5.0),
    ])
    # quantity / invested untouched by income+cost rows
    assert pos.quantity == 10.0
    assert pos.net_invested == 20.0
    assert pos.income_total == 40.0            # 50 + 5 - 10 - 5
    assert pos.total_return == pytest.approx(70.0)  # unrealized 30 + income 40


# --- amount-based holdings (renda fixa / caixinha, quantity 0) ------------

def test_amount_based_holding_treats_quantity_as_one(service):
    # A CDB: contributed 1000 (quantity 0), current total 1100.
    inv = _holding(asset_type=AssetType.RENDA_FIXA, current_price=1100.0)
    pos = service.compute_position(inv, [_txn(InvestmentTxnType.CONTRIBUTION, total=1000.0)])
    assert pos.quantity == 0.0
    assert pos.avg_unit_price == 0.0           # guarded: quantity not > 0
    assert pos.market_value == 1100.0          # current_price * 1
    assert pos.net_invested == 1000.0
    assert pos.unrealized_gain == 100.0
    assert pos.return_pct == pytest.approx(10.0)


# --- savings-box goal progress -------------------------------------------

def test_goal_progress_pct_for_savings_box(service):
    inv = _holding(asset_type=AssetType.SAVINGS_BOX, current_price=1100.0, goal_amount=2000.0)
    pos = service.compute_position(inv, [_txn(InvestmentTxnType.CONTRIBUTION, total=1000.0)])
    assert pos.goal_progress_pct == pytest.approx(55.0)  # 1100 / 2000 * 100


def test_goal_progress_pct_zero_without_goal(service):
    inv = _holding(asset_type=AssetType.RENDA_FIXA, current_price=1100.0)
    pos = service.compute_position(inv, [_txn(InvestmentTxnType.CONTRIBUTION, total=1000.0)])
    assert pos.goal_progress_pct == 0.0


# --- portfolio aggregation ------------------------------------------------

def test_portfolio_sums_positions(service):
    a = _holding(current_price=5.0)   # buy 10 @2 -> invested 20, mv 50
    b = _holding(asset_type=AssetType.RENDA_FIXA, current_price=1100.0)  # amount-based
    txns = {
        a.id: [_txn(InvestmentTxnType.BUY, quantity=10, total=20.0),
               _txn(InvestmentTxnType.DIVIDEND, total=5.0)],
        b.id: [_txn(InvestmentTxnType.CONTRIBUTION, total=1000.0)],
    }
    summary = service.compute_portfolio([a, b], txns)
    assert summary.total_invested == pytest.approx(1020.0)       # 20 + 1000
    assert summary.total_market_value == pytest.approx(1150.0)   # 50 + 1100
    assert summary.total_income == pytest.approx(5.0)
    # gain = market_value - invested + income = 1150 - 1020 + 5
    assert summary.total_gain == pytest.approx(135.0)
    assert summary.return_pct == pytest.approx(135.0 / 1020.0 * 100.0)


def test_empty_portfolio_is_zeroed(service):
    summary = service.compute_portfolio([], {})
    assert summary.total_invested == 0.0
    assert summary.total_market_value == 0.0
    assert summary.total_gain == 0.0
    assert summary.return_pct == 0.0
