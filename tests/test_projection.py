"""Tests for the pure yield-projection math (src/domain/services/projection.py).

Rates in this module are annual *fractions* (0.12 == 12% a.a.). These cover
benchmark resolution, compounding, income, contribution series, and goal ETAs.
"""

import pytest

from src.domain.services import projection as p


# --- effective_annual_rate ------------------------------------------------

def test_prefixed_rate_is_percent_over_100():
    assert p.effective_annual_rate(12.0, "prefixed") == pytest.approx(0.12)


def test_none_yield_rate_returns_none():
    assert p.effective_annual_rate(None, "prefixed") is None


def test_empty_index_defaults_to_prefixed():
    assert p.effective_annual_rate(10.0, "") == pytest.approx(0.10)


def test_cdi_percentage_of_benchmark():
    # 100% of a 11% CDI -> 0.11
    assert p.effective_annual_rate(100.0, "cdi", cdi=11.0) == pytest.approx(0.11)
    # 90% of CDI
    assert p.effective_annual_rate(90.0, "cdi", cdi=11.0) == pytest.approx(0.099)


def test_selic_percentage_of_benchmark():
    assert p.effective_annual_rate(100.0, "selic", selic=10.5) == pytest.approx(0.105)


def test_ipca_plus_is_additive():
    # IPCA 4% + 5% spread
    assert p.effective_annual_rate(5.0, "ipca_plus", ipca_annual=4.0) == pytest.approx(0.09)


def test_selic_plus_and_cdi_plus_are_additive():
    assert p.effective_annual_rate(0.07, "selic_plus", selic=10.5) == pytest.approx(0.1057)
    assert p.effective_annual_rate(2.0, "cdi_plus", cdi=11.0) == pytest.approx(0.13)


def test_missing_benchmark_returns_none():
    assert p.effective_annual_rate(100.0, "cdi", cdi=None) is None
    assert p.effective_annual_rate(100.0, "selic", selic=None) is None
    assert p.effective_annual_rate(5.0, "ipca_plus", ipca_annual=None) is None


def test_unknown_index_returns_none():
    assert p.effective_annual_rate(10.0, "bogus") is None


# --- compounding + income -------------------------------------------------

def test_monthly_rate_compounds_to_annual():
    r = p.monthly_rate(0.12)
    assert (1.0 + r) ** 12 == pytest.approx(1.12)


def test_annual_and_monthly_income():
    assert p.annual_income(1000.0, 0.12) == pytest.approx(120.0)
    assert p.monthly_income(1000.0, 0.12) == pytest.approx(1000.0 * p.monthly_rate(0.12))


def test_project_value_over_12_months_equals_one_annual_step():
    assert p.project_value(1000.0, 0.12, 12) == pytest.approx(1120.0)


def test_project_value_zero_months_is_unchanged():
    assert p.project_value(1000.0, 0.12, 0) == pytest.approx(1000.0)


# --- contribution series --------------------------------------------------

def test_contribution_series_with_zero_rate_is_plain_sum():
    series = p.project_value_with_contributions(1000.0, 0.0, [100.0, 100.0])
    assert series == [1000.0, 1100.0, 1200.0]


def test_contribution_series_length_and_start():
    series = p.project_value_with_contributions(500.0, 0.12, [50.0, 50.0, 50.0])
    assert len(series) == 4          # value + one entry per contribution month
    assert series[0] == 500.0
    # each step grows then adds the contribution, so it beats the plain sum
    assert series[-1] > 500.0 + 150.0


# --- goal ETA -------------------------------------------------------------

def test_goal_already_reached_returns_zero():
    assert p.goal_eta_months(2000.0, 1000.0, 0.10) == 0


def test_goal_unreachable_without_growth_or_deposits_returns_none():
    assert p.goal_eta_months(100.0, 1000.0, 0.0, monthly_deposit=0.0) is None


def test_goal_reached_via_monthly_deposit():
    # 0 start, no yield, 100/mo toward 1000 -> 10 months
    assert p.goal_eta_months(0.0, 1000.0, 0.0, monthly_deposit=100.0) == 10


def test_goal_reached_faster_with_yield():
    no_yield = p.goal_eta_months(0.0, 1000.0, 0.0, monthly_deposit=100.0)
    with_yield = p.goal_eta_months(0.0, 1000.0, 0.12, monthly_deposit=100.0)
    assert with_yield <= no_yield


def test_nonpositive_goal_returns_zero():
    assert p.goal_eta_months(0.0, 0.0, 0.10) == 0
