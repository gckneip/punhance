import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.domain.entities.dashboard_widget import DashboardWidgetKind


@dataclass
class PresetDefinition:
    preset_id: str
    title: str
    kind: DashboardWidgetKind
    default_row_span: int
    default_col_span: int
    config: Dict[str, Any] = field(default_factory=dict)


def _rolling_months(amount: int) -> dict:
    return {"mode": "rolling", "unit": "months", "amount": amount}


def _this_month() -> dict:
    return {"mode": "calendar", "period": "month", "offset": 0}


DEFAULT_PRESETS = [
    PresetDefinition(
        preset_id="monthly_net_trend",
        title="Monthly Net Trend (6 months)",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "line", "metrics": ["net"], "group_by": "month",
            "date_range": _rolling_months(6), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="income_vs_expenses",
        title="Income vs Expenses (6 months)",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "bar", "metrics": ["income", "expenses"], "group_by": "month",
            "date_range": _rolling_months(6), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="spending_by_category",
        title="Spending by Category (This Month)",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "pie", "metrics": ["expenses"], "group_by": "category",
            "date_range": _this_month(), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="spending_by_item",
        title="Spending by Item (This Month)",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "table", "metrics": ["expenses"], "group_by": "product",
            "date_range": _this_month(), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="account_balances",
        title="Account Balances",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "bar", "metrics": ["balance"], "group_by": "account",
            "date_range": _this_month(), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="upcoming_installments",
        title="Upcoming Installments (Next 30 Days)",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "table", "data_source": "upcoming_installments",
            "days_ahead": 30, "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="upcoming_recurring_events",
        title="Upcoming Recurring Events (Next 30 Days)",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "table", "data_source": "upcoming_recurring_events",
            "days_ahead": 30, "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="credit_card_utilization",
        title="Credit Card Utilization",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=3,
        default_col_span=6,
        config={
            "chart_type": "bar", "metrics": ["credit_card_debt"], "group_by": "credit_card",
            "date_range": _this_month(), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="monthly_income_stat",
        title="Monthly Income",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=1,
        default_col_span=3,
        config={
            "chart_type": "stat", "metrics": ["income"], "group_by": "none",
            "date_range": _this_month(), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="monthly_expenses_stat",
        title="Monthly Expenses",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=1,
        default_col_span=3,
        config={
            "chart_type": "stat", "metrics": ["expenses"], "group_by": "none",
            "date_range": _this_month(), "filters": {},
        },
    ),
    PresetDefinition(
        preset_id="monthly_net_stat",
        title="Monthly Net",
        kind=DashboardWidgetKind.GENERIC,
        default_row_span=1,
        default_col_span=3,
        config={
            "chart_type": "stat", "metrics": ["net"], "group_by": "none",
            "date_range": _this_month(), "filters": {},
        },
    ),
]


def find_preset(preset_id: str) -> Optional[PresetDefinition]:
    return next((p for p in DEFAULT_PRESETS if p.preset_id == preset_id), None)


def clone_preset_config(preset: PresetDefinition) -> Dict[str, Any]:
    return copy.deepcopy(preset.config)


def default_span_for_chart_type(chart_type: str) -> tuple:
    return (1, 3) if chart_type == "stat" else (3, 6)
