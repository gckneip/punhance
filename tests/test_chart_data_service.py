"""Tests for ChartDataService pure logic: date-range resolution, month
helpers, linear forecasting, metric/filter helpers, spec parsing, and the
income/expense classification (investment-category and uncleared-card-charge
exclusions). The orchestration methods that fan out across 15 repositories are
left to higher-level/manual testing; these cover the self-contained logic.
"""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.services.chart_data_service import (
    ChartDataService,
    ChartFilters,
    DateRangeSpec,
    GroupByDimension,
    MetricType,
    _add_one_month,
    _append_forecast,
    _frequency_label,
    _linear_forecast,
    _month_iteration_bounds,
    _month_range,
    _shift_months,
    validate_metric_group_by,
)
from tests._fakes import FakeCategoryRepo


# --- validate_metric_group_by --------------------------------------------

def test_validate_metric_group_by_allows_valid_pair():
    validate_metric_group_by(MetricType.EXPENSES, GroupByDimension.PRODUCT)  # no raise


def test_validate_metric_group_by_rejects_invalid_pair():
    with pytest.raises(ValueError):
        # PRODUCT is only valid for EXPENSES, not INCOME.
        validate_metric_group_by(MetricType.INCOME, GroupByDimension.PRODUCT)


def test_validate_metric_group_by_rejects_credit_card_for_income():
    with pytest.raises(ValueError):
        validate_metric_group_by(MetricType.INCOME, GroupByDimension.CREDIT_CARD)


# --- resolve_date_range ---------------------------------------------------

TODAY = date(2026, 6, 15)


def test_resolve_fixed_makes_date_to_exclusive():
    spec = DateRangeSpec(mode="fixed", date_from=date(2026, 1, 1), date_to=date(2026, 1, 31))
    df, dt = ChartDataService.resolve_date_range(spec, today=TODAY)
    assert df == date(2026, 1, 1)
    assert dt == date(2026, 2, 1)          # 01-31 + 1 day, exclusive upper bound


def test_resolve_fixed_all_time_is_none_none():
    spec = DateRangeSpec(mode="fixed")
    assert ChartDataService.resolve_date_range(spec, today=TODAY) == (None, None)


def test_resolve_rolling_days():
    spec = DateRangeSpec(mode="rolling", unit="days", amount=7)
    df, dt = ChartDataService.resolve_date_range(spec, today=TODAY)
    assert df == date(2026, 6, 8)          # today - 7 days
    assert dt == date(2026, 6, 16)         # today + 1 day


def test_resolve_rolling_months_includes_current_month():
    spec = DateRangeSpec(mode="rolling", unit="months", amount=3)
    df, dt = ChartDataService.resolve_date_range(spec, today=TODAY)
    assert df == date(2026, 4, 1)          # 3 months back incl. current = Apr
    assert dt == date(2026, 7, 1)          # start of next month


def test_resolve_calendar_month_offset():
    spec = DateRangeSpec(mode="calendar", period="month", offset=-1)
    df, dt = ChartDataService.resolve_date_range(spec, today=TODAY)
    assert df == date(2026, 5, 1)
    assert dt == date(2026, 6, 1)


def test_resolve_calendar_year_offset():
    spec = DateRangeSpec(mode="calendar", period="year", offset=0)
    df, dt = ChartDataService.resolve_date_range(spec, today=TODAY)
    assert df == date(2026, 1, 1)
    assert dt == date(2027, 1, 1)


def test_resolve_rejects_unknown_mode_and_unit():
    with pytest.raises(ValueError):
        ChartDataService.resolve_date_range(DateRangeSpec(mode="bogus"), today=TODAY)
    with pytest.raises(ValueError):
        ChartDataService.resolve_date_range(
            DateRangeSpec(mode="rolling", unit="weeks", amount=1), today=TODAY
        )


# --- spec / filter parsing ------------------------------------------------

def test_daterangespec_from_dict_parses_iso_dates():
    spec = DateRangeSpec.from_dict({"mode": "fixed", "date_from": "2026-01-01", "date_to": "2026-02-28"})
    assert spec.date_from == date(2026, 1, 1)
    assert spec.date_to == date(2026, 2, 28)


def test_daterangespec_from_dict_without_dates():
    spec = DateRangeSpec.from_dict({"mode": "rolling", "unit": "months", "amount": 6})
    assert spec.date_from is None and spec.date_to is None
    assert spec.unit == "months" and spec.amount == 6


def test_chartfilters_from_dict_coerces_empty_to_none():
    f = ChartFilters.from_dict({"account_ids": [], "category_ids": ["c1"]})
    assert f.account_ids is None          # empty list -> None (no filtering)
    assert f.category_ids == ["c1"]


def test_chartfilters_from_dict_handles_none():
    f = ChartFilters.from_dict(None)
    assert f.account_ids is None and f.category_ids is None


# --- month helpers --------------------------------------------------------

def test_add_one_month_rolls_year():
    assert _add_one_month(date(2026, 1, 15)) == date(2026, 2, 1)
    assert _add_one_month(date(2026, 12, 9)) == date(2027, 1, 1)


def test_shift_months_forward_and_back():
    assert _shift_months(date(2026, 6, 1), 3) == date(2026, 9, 1)
    assert _shift_months(date(2026, 1, 1), -2) == date(2025, 11, 1)
    assert _shift_months(date(2026, 1, 1), 0) == date(2026, 1, 1)


def test_month_range_is_half_open():
    # date_to is exclusive, so a range ending on the 1st stops before that month.
    months = list(_month_range(date(2026, 1, 10), date(2026, 4, 1)))
    assert months == [(2026, 1), (2026, 2), (2026, 3)]


def test_month_iteration_bounds_substitutes_defaults():
    df, dt = _month_iteration_bounds(None, None)
    assert df == date(2000, 1, 1)                      # "beginning of time"
    assert dt == date.today() + timedelta(days=1)      # through today, exclusive


def test_month_iteration_bounds_passes_through_concrete_bounds():
    df, dt = _month_iteration_bounds(date(2026, 1, 1), date(2026, 3, 1))
    assert (df, dt) == (date(2026, 1, 1), date(2026, 3, 1))


# --- linear forecast ------------------------------------------------------

def test_linear_forecast_continues_slope():
    # Perfect line 0,1,2,3 -> next points are 4,5.
    assert _linear_forecast([0.0, 1.0, 2.0, 3.0], 2) == [4.0, 5.0]


def test_linear_forecast_flat_series_stays_flat():
    assert _linear_forecast([5.0, 5.0, 5.0], 2) == [5.0, 5.0]


def test_linear_forecast_degenerate_inputs():
    assert _linear_forecast([], 3) == [0.0, 0.0, 0.0]      # no history -> zeros
    assert _linear_forecast([7.0], 2) == [7.0, 7.0]        # single point -> repeat
    assert _linear_forecast([1.0, 2.0, 3.0], 0) == []      # no steps
    assert _linear_forecast([1.0, 2.0, 3.0], -1) == []


# --- append forecast ------------------------------------------------------

def test_append_forecast_extends_labels_and_series():
    labels = ["2026-01", "2026-02", "2026-03"]
    series = {"net": [10.0, 20.0, 30.0]}
    count = _append_forecast(labels, series, 2)
    assert count == 2
    assert labels == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
    assert series["net"] == [10.0, 20.0, 30.0, 40.0, 50.0]


def test_append_forecast_rolls_label_year():
    labels = ["2026-11", "2026-12"]
    series = {"net": [1.0, 2.0]}
    _append_forecast(labels, series, 2)
    assert labels[-2:] == ["2027-01", "2027-02"]


def test_append_forecast_is_noop_without_months_or_labels():
    labels, series = ["2026-01"], {"net": [1.0]}
    assert _append_forecast(labels, series, 0) == 0
    assert labels == ["2026-01"] and series["net"] == [1.0]
    assert _append_forecast([], {"net": []}, 3) == 0


# --- frequency label ------------------------------------------------------

def _freq_rule(frequency, interval):
    return SimpleNamespace(frequency=SimpleNamespace(value=frequency), interval=interval)


def test_frequency_label_singular_interval():
    assert _frequency_label(_freq_rule("monthly", 1)) == "Monthly"
    assert _frequency_label(_freq_rule("daily", 1)) == "Daily"


def test_frequency_label_plural_interval():
    assert _frequency_label(_freq_rule("weekly", 2)) == "Every 2 weeks"
    assert _frequency_label(_freq_rule("yearly", 3)) == "Every 3 years"


# --- _metric_values -------------------------------------------------------

def test_metric_values_only_includes_requested_metrics():
    vals = ChartDataService._metric_values([MetricType.NET], income=100.0, expenses=30.0)
    assert vals == {"net": 70.0}


def test_metric_values_income_expenses_and_net():
    vals = ChartDataService._metric_values(
        [MetricType.INCOME, MetricType.EXPENSES, MetricType.NET], 100.0, 30.0
    )
    assert vals == {"income": 100.0, "expenses": 30.0, "net": 70.0}


# --- _matches_filters -----------------------------------------------------

def _ev(**kwargs):
    base = dict(
        event_type=EventType.EXPENSE, event_date=date(2026, 1, 1),
        description="t", amount=1.0,
    )
    base.update(kwargs)
    return FinancialEvent(**base)


def test_matches_filters_none_matches_everything():
    assert ChartDataService._matches_filters(_ev(), None) is True


def test_matches_filters_by_account_or_destination():
    f = ChartFilters(account_ids=["a1"])
    assert ChartDataService._matches_filters(_ev(account_id="a1"), f) is True
    assert ChartDataService._matches_filters(_ev(destination_account_id="a1"), f) is True
    assert ChartDataService._matches_filters(_ev(account_id="a2"), f) is False


def test_matches_filters_all_dimensions_must_pass():
    f = ChartFilters(category_ids=["c1"], credit_card_ids=["cc1"])
    assert ChartDataService._matches_filters(_ev(category_id="c1", credit_card_id="cc1"), f) is True
    assert ChartDataService._matches_filters(_ev(category_id="c1", credit_card_id="cc2"), f) is False


def test_matches_filters_by_counterparty():
    f = ChartFilters(counterparty_ids=["p1"])
    assert ChartDataService._matches_filters(_ev(counterparty_id="p1"), f) is True
    assert ChartDataService._matches_filters(_ev(counterparty_id="p2"), f) is False


# --- _classify ------------------------------------------------------------

def _service_with_cats(investment_ids=()):
    # _classify only touches the category repository; the other 14 deps are
    # unused on this path, so None is safe here.
    svc = ChartDataService.__new__(ChartDataService)
    svc._category_repository = FakeCategoryRepo(investment_ids)
    return svc


def test_classify_splits_income_and_expenses():
    svc = _service_with_cats()
    income, expenses = svc._classify([
        _ev(event_type=EventType.INCOME, amount=100.0),
        _ev(event_type=EventType.REFUND, amount=20.0),
        _ev(event_type=EventType.EXPENSE, amount=30.0),
        _ev(event_type=EventType.CARD_PAYMENT, amount=15.0),
    ])
    assert income == 120.0        # income + refund
    assert expenses == 45.0       # expense + card payment


def test_classify_excludes_investment_category_events():
    svc = _service_with_cats(investment_ids=["inv"])
    income, expenses = svc._classify([
        _ev(event_type=EventType.INCOME, amount=100.0, category_id="inv"),
        _ev(event_type=EventType.EXPENSE, amount=30.0, category_id="inv"),
        _ev(event_type=EventType.EXPENSE, amount=10.0),
    ])
    assert income == 0.0          # investment-category income ignored
    assert expenses == 10.0       # only the non-investment expense counts


def test_classify_excludes_uncleared_card_charges():
    svc = _service_with_cats()
    # An EXPENSE tagged to a card is an uncleared charge -> skipped to avoid
    # double counting with its later CARD_PAYMENT.
    income, expenses = svc._classify([
        _ev(event_type=EventType.EXPENSE, amount=40.0, credit_card_id="cc1"),
        _ev(event_type=EventType.EXPENSE, amount=25.0),
    ])
    assert income == 0.0
    assert expenses == 25.0


def test_classify_ignores_transfers_and_investments():
    svc = _service_with_cats()
    income, expenses = svc._classify([
        _ev(event_type=EventType.TRANSFER, amount=50.0),
        _ev(event_type=EventType.INVESTMENT, amount=60.0),
        _ev(event_type=EventType.REDEMPTION, amount=70.0),
    ])
    assert income == 0.0 and expenses == 0.0
