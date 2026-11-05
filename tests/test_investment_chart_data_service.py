"""Tests for InvestmentChartDataService.

This service is mostly orchestration: it pulls from the investment/indicator
use cases and the snapshot repo, then groups, sorts, filters, and shapes the
result into (labels, series)/stat/table forms. The yield math itself lives in
`projection` (tested separately), so here we use `prefixed` yields — which
resolve to yield_rate/100 with no benchmark needed — and assert the service's
own aggregation and the relational properties of its output.
"""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.domain.entities.investment import AssetType
from src.domain.services import projection
from src.domain.services.investment_chart_data_service import (
    InvestmentChartDataService,
    _add_months,
)
from src.domain.services.investment_chart_types import (
    AllocationDimension,
    HoldingMetric,
    PortfolioMetric,
)


# --- fakes ----------------------------------------------------------------

class FakeInvestmentUC:
    def __init__(self, investments=(), summary=None, schedules=None):
        self._investments = list(investments)
        self._summary = summary
        self._schedules = schedules or {}

    def get_portfolio_summary(self):
        return self._summary

    def list_investments(self):
        return list(self._investments)

    def list_schedules(self, investment_id):
        return list(self._schedules.get(investment_id, []))


class FakeIndicatorUC:
    def __init__(self, series=None, latest=None):
        self._series = series or {}
        self._latest = latest or {}

    def get_series(self, key):
        return list(self._series.get(key, []))

    def get_latest(self, key):
        return self._latest.get(key)


class FakeSnapshotRepo:
    def __init__(self, snapshots=()):
        self._snapshots = list(snapshots)

    def find_all(self):
        return list(self._snapshots)


def _holding(name="H", **kwargs):
    base = dict(
        id=name.lower(),
        name=name,
        currency="BRL",
        asset_type=AssetType.RENDA_FIXA,
        market_value=0.0,
        net_invested=0.0,
        unrealized_gain=0.0,
        total_return=0.0,
        income_total=0.0,
        return_pct=0.0,
        quantity=0.0,
        goal_amount=None,
        goal_date=None,
        monthly_contribution=0.0,
        yield_rate=None,
        yield_index="prefixed",
        maturity_date=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _service(investments=(), summary=None, schedules=None, snapshots=None,
             series=None, latest=None):
    return InvestmentChartDataService(
        FakeInvestmentUC(investments, summary, schedules),
        FakeIndicatorUC(series, latest),
        FakeSnapshotRepo(snapshots) if snapshots is not None else None,
    )


# --- _add_months ----------------------------------------------------------

def test_add_months_snaps_to_first_and_rolls_year():
    assert _add_months(date(2026, 1, 15), 0) == date(2026, 1, 1)
    assert _add_months(date(2026, 11, 20), 3) == date(2027, 2, 1)


# --- portfolio stat -------------------------------------------------------

def test_portfolio_stat_reads_summary_attribute():
    summary = SimpleNamespace(total_invested=1000.0, total_market_value=1250.0)
    svc = _service(summary=summary)
    assert svc.get_portfolio_stat(PortfolioMetric.TOTAL_MARKET_VALUE) == 1250.0


def test_portfolio_stat_defaults_missing_attribute_to_zero():
    svc = _service(summary=SimpleNamespace())
    assert svc.get_portfolio_stat(PortfolioMetric.TOTAL_GAIN) == 0.0


# --- portfolio value series ----------------------------------------------

def test_portfolio_value_series_without_snapshot_repo_is_empty():
    svc = _service()  # snapshots repo is None
    assert svc.get_portfolio_value_series() == ([], {})


def test_portfolio_value_series_with_no_snapshots_is_empty():
    svc = _service(snapshots=[])
    assert svc.get_portfolio_value_series() == ([], {})


def test_portfolio_value_series_builds_dates_and_metric_series():
    snaps = [
        SimpleNamespace(date="2026-01-01", total_market_value=100.0, total_invested=90.0),
        SimpleNamespace(date="2026-02-01", total_market_value=130.0, total_invested=110.0),
    ]
    svc = _service(snapshots=snaps)
    dates, series = svc.get_portfolio_value_series()
    assert dates == ["2026-01-01", "2026-02-01"]
    assert series["total_market_value"] == [100.0, 130.0]
    assert series["total_invested"] == [90.0, 110.0]


# --- allocation -----------------------------------------------------------

def test_allocation_groups_by_asset_type_sorted_desc():
    svc = _service([
        _holding("A", asset_type=AssetType.RENDA_FIXA, market_value=100.0),
        _holding("B", asset_type=AssetType.CRYPTO, market_value=300.0),
        _holding("C", asset_type=AssetType.RENDA_FIXA, market_value=50.0),
    ])
    labels, values = svc.get_allocation(AllocationDimension.ASSET_TYPE, HoldingMetric.MARKET_VALUE)
    assert labels == [AssetType.CRYPTO.value, AssetType.RENDA_FIXA.value]
    assert values == [300.0, 150.0]        # RF 100+50 merged


def test_allocation_groups_by_currency():
    svc = _service([
        _holding("A", currency="BRL", market_value=100.0),
        _holding("B", currency="USD", market_value=400.0),
    ])
    labels, values = svc.get_allocation(AllocationDimension.CURRENCY, HoldingMetric.MARKET_VALUE)
    assert labels == ["USD", "BRL"]
    assert values == [400.0, 100.0]


# --- holdings breakdown ---------------------------------------------------

def test_holdings_breakdown_sorted_by_magnitude():
    svc = _service([
        _holding("Small", market_value=10.0),
        _holding("Big", market_value=90.0),
        _holding("Mid", market_value=40.0),
    ])
    labels, values = svc.get_holdings_breakdown(HoldingMetric.MARKET_VALUE)
    assert labels == ["Big", "Mid", "Small"]
    assert values == [90.0, 40.0, 10.0]


def test_holdings_breakdown_respects_top_n():
    svc = _service([
        _holding("Small", market_value=10.0),
        _holding("Big", market_value=90.0),
        _holding("Mid", market_value=40.0),
    ])
    labels, values = svc.get_holdings_breakdown(HoldingMetric.MARKET_VALUE, top_n=2)
    assert labels == ["Big", "Mid"]
    assert values == [90.0, 40.0]


def test_holdings_passthrough():
    holdings = [_holding("A"), _holding("B")]
    svc = _service(holdings)
    assert svc.get_holdings() == holdings


# --- savings goals --------------------------------------------------------

def test_savings_goals_filters_and_computes_progress():
    svc = _service([
        _holding("Box", asset_type=AssetType.SAVINGS_BOX, market_value=250.0,
                 goal_amount=1000.0, monthly_contribution=100.0),
        _holding("NoGoalBox", asset_type=AssetType.SAVINGS_BOX, market_value=50.0,
                 goal_amount=None),
        _holding("NotABox", asset_type=AssetType.RENDA_FIXA, market_value=500.0,
                 goal_amount=1000.0),
    ])
    rows = svc.get_savings_goals()
    assert len(rows) == 1               # only the box with a goal
    row = rows[0]
    assert row["name"] == "Box"
    assert row["pct"] == 25.0
    assert row["remaining"] == 750.0
    assert row["eta_months"] is not None  # reachable via monthly contributions


def test_savings_goals_sorted_by_completion_desc():
    svc = _service([
        _holding("Low", asset_type=AssetType.SAVINGS_BOX, market_value=100.0,
                 goal_amount=1000.0, monthly_contribution=10.0),
        _holding("High", asset_type=AssetType.SAVINGS_BOX, market_value=800.0,
                 goal_amount=1000.0, monthly_contribution=10.0),
    ])
    rows = svc.get_savings_goals()
    assert [r["name"] for r in rows] == ["High", "Low"]


# --- income projections ---------------------------------------------------

def test_income_projections_skip_zero_value_and_no_rate():
    svc = _service([
        _holding("Yielding", market_value=1000.0, yield_rate=12.0),   # prefixed 12%
        _holding("NoRate", market_value=1000.0, yield_rate=None),     # unresolvable
        _holding("Empty", market_value=0.0, yield_rate=12.0),         # no value
    ])
    rows = svc.get_income_projections()
    assert [r["name"] for r in rows] == ["Yielding"]
    row = rows[0]
    assert row["rate"] == 0.12
    assert row["annual"] == pytest.approx(projection.annual_income(1000.0, 0.12))
    assert row["monthly"] == pytest.approx(projection.monthly_income(1000.0, 0.12))
    assert row["annual_investment"] == 0.0   # no schedules configured


def test_portfolio_projected_income_sums_rows():
    svc = _service([
        _holding("A", market_value=1000.0, yield_rate=10.0),
        _holding("B", market_value=2000.0, yield_rate=5.0),
    ])
    rows = svc.get_income_projections()
    agg = svc.get_portfolio_projected_income()
    assert agg["annual"] == pytest.approx(sum(r["annual"] for r in rows))
    assert agg["monthly"] == pytest.approx(sum(r["monthly"] for r in rows))


def test_income_projections_sorted_by_annual_desc():
    svc = _service([
        _holding("Small", market_value=100.0, yield_rate=10.0),
        _holding("Big", market_value=10000.0, yield_rate=10.0),
    ])
    rows = svc.get_income_projections()
    assert [r["name"] for r in rows] == ["Big", "Small"]


# --- upcoming maturities --------------------------------------------------

def test_upcoming_maturities_sorted_and_skips_undated():
    today = date.today()
    soon = (today + timedelta(days=10)).isoformat()
    later = (today + timedelta(days=100)).isoformat()
    svc = _service([
        _holding("Later", maturity_date=later, market_value=1.0),
        _holding("Soon", maturity_date=soon, market_value=1.0),
        _holding("NoMaturity", maturity_date=None),
        _holding("Garbage", maturity_date="not-a-date"),
    ])
    rows = svc.get_upcoming_maturities()
    assert [r["name"] for r in rows] == ["Soon", "Later"]
    assert rows[0]["days_remaining"] == 10


def test_upcoming_maturities_negative_for_matured():
    today = date.today()
    past = (today - timedelta(days=5)).isoformat()
    svc = _service([_holding("Matured", maturity_date=past, market_value=1.0)])
    rows = svc.get_upcoming_maturities()
    assert rows[0]["days_remaining"] == -5


# --- value at maturity ----------------------------------------------------

def test_value_at_maturity_requires_date_and_rate():
    today = date.today()
    mat = (today + timedelta(days=365)).isoformat()
    svc = _service([
        _holding("Good", maturity_date=mat, market_value=1000.0, yield_rate=10.0),
        _holding("NoRate", maturity_date=mat, market_value=1000.0, yield_rate=None),
        _holding("NoDate", maturity_date=None, yield_rate=10.0),
    ])
    rows = svc.get_value_at_maturity()
    assert [r["name"] for r in rows] == ["Good"]
    row = rows[0]
    assert row["gain"] == pytest.approx(row["projected"] - row["current"])
    assert row["projected"] > row["current"]   # positive yield grows it


def test_value_at_maturity_sorted_by_date():
    today = date.today()
    far = (today + timedelta(days=700)).isoformat()
    near = (today + timedelta(days=100)).isoformat()
    svc = _service([
        _holding("Far", maturity_date=far, market_value=100.0, yield_rate=5.0),
        _holding("Near", maturity_date=near, market_value=100.0, yield_rate=5.0),
    ])
    rows = svc.get_value_at_maturity()
    assert [r["name"] for r in rows] == ["Near", "Far"]


# --- effective rate pct ---------------------------------------------------

def test_effective_rate_pct_found():
    svc = _service([_holding("A", yield_rate=12.5)])
    assert svc.get_effective_rate_pct("a") == pytest.approx(12.5)


def test_effective_rate_pct_unknown_asset_is_none():
    svc = _service([_holding("A", yield_rate=12.5)])
    assert svc.get_effective_rate_pct("missing") is None


def test_effective_rate_pct_no_rate_is_none():
    svc = _service([_holding("A", yield_rate=None)])
    assert svc.get_effective_rate_pct("a") is None


# --- projected value series ----------------------------------------------

def test_projected_value_series_labels_span_months_plus_one():
    svc = _service([_holding("A", market_value=1000.0, yield_rate=10.0)])
    labels, series = svc.get_projected_value_series(months=6)
    assert len(labels) == 7
    assert len(series["projected_value"]) == 7
    assert series["projected_value"][0] == pytest.approx(1000.0)  # month 0 = current


def test_projected_value_series_empty_without_holdings():
    assert _service([]).get_projected_value_series() == ([], {})


def test_projected_value_by_asset_filters_by_ids():
    svc = _service([
        _holding("A", market_value=1000.0, yield_rate=10.0),
        _holding("B", market_value=500.0, yield_rate=10.0),
    ])
    labels, series = svc.get_projected_value_by_asset(months=3, asset_ids=["a"])
    assert len(labels) == 4
    assert set(series.keys()) == {"A"}


def test_projected_value_by_asset_empty_when_filter_matches_nothing():
    svc = _service([_holding("A", market_value=1.0, yield_rate=1.0)])
    assert svc.get_projected_value_by_asset(asset_ids=["nope"]) == ([], {})


# --- simulate projection --------------------------------------------------

def test_simulate_projection_new_investment_at_given_rate():
    svc = _service()
    totals = svc.simulate_projection(12, [{"initial": 1000.0, "monthly": 0.0, "rate_pct": 10.0}])
    assert len(totals) == 13
    assert totals[0] == pytest.approx(1000.0)
    assert totals[-1] == pytest.approx(project_final(1000.0, 0.10, 12))


def test_simulate_projection_reuses_existing_asset_rate():
    svc = _service([_holding("A", market_value=0.0, yield_rate=10.0)])
    totals = svc.simulate_projection(6, [{"initial": 500.0, "asset_id": "a"}])
    assert totals[0] == pytest.approx(500.0)
    assert totals[-1] == pytest.approx(project_final(500.0, 0.10, 6))


def test_simulate_projection_sums_multiple_sims():
    svc = _service()
    one = svc.simulate_projection(6, [{"initial": 100.0, "rate_pct": 0.0}])
    two = svc.simulate_projection(6, [
        {"initial": 100.0, "rate_pct": 0.0},
        {"initial": 200.0, "rate_pct": 0.0},
    ])
    assert two[-1] == pytest.approx(one[-1] + 200.0)


# --- scheduled contributions / projected total invested -------------------

def test_scheduled_contributions_zero_without_schedules():
    svc = _service([_holding("A")])
    assert svc._scheduled_monthly_contributions("a", 12) == [0.0] * 12


def test_scheduled_contributions_empty_for_non_positive_months():
    svc = _service([_holding("A")])
    assert svc._scheduled_monthly_contributions("a", 0) == []


def test_projected_total_invested_without_schedules_is_portfolio_stat():
    summary = SimpleNamespace(total_invested=1500.0)
    svc = _service([_holding("A")], summary=summary)
    assert svc.get_projected_total_invested(12) == 1500.0


# --- indicators -----------------------------------------------------------

def test_indicator_series_splits_dates_and_values():
    series = [SimpleNamespace(date="2026-01-01", value=1.1),
              SimpleNamespace(date="2026-02-01", value=1.2)]
    svc = _service(series={"ipca": series})
    dates, values = svc.get_indicator_series("ipca")
    assert dates == ["2026-01-01", "2026-02-01"]
    assert values == [1.1, 1.2]


def test_indicator_series_empty_when_uncached():
    svc = _service()
    assert svc.get_indicator_series("cdi") == ([], [])


def test_indicator_latest_value_or_none():
    svc = _service(latest={"selic": SimpleNamespace(value=11.25)})
    assert svc.get_indicator_latest("selic") == 11.25
    assert svc.get_indicator_latest("cdi") is None


def test_indicator_info_from_catalog():
    svc = _service()
    # "cdi" is a known catalog indicator; a bogus key returns None.
    assert svc.get_indicator_info("cdi") is not None
    assert svc.get_indicator_info("not-an-indicator") is None


# Helper mirroring the service's compound-growth of a lump sum (no contributions).
def project_final(initial, rate, months):
    return projection.project_value_with_contributions(initial, rate, [0.0] * months)[-1]
