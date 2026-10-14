import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class InvestmentPresetDefinition:
    preset_id: str
    title: str  # English fallback; display sites prefer title_key
    default_row_span: int
    default_col_span: int
    config: Dict[str, Any] = field(default_factory=dict)
    title_key: str = ""

    @property
    def display_title_key(self) -> str:
        return self.title_key or f"investment_preset.{self.preset_id}"


DEFAULT_INVESTMENT_PRESETS = [
    InvestmentPresetDefinition(
        preset_id="portfolio_market_value_stat", title="Market Value",
        title_key="investment_preset.portfolio_market_value_stat",
        default_row_span=1, default_col_span=3,
        config={"source": "portfolio_stat", "chart_type": "stat", "metric": "total_market_value"},
    ),
    InvestmentPresetDefinition(
        preset_id="portfolio_invested_stat", title="Total Invested",
        title_key="investment_preset.portfolio_invested_stat",
        default_row_span=1, default_col_span=3,
        config={"source": "portfolio_stat", "chart_type": "stat", "metric": "total_invested"},
    ),
    InvestmentPresetDefinition(
        preset_id="portfolio_gain_stat", title="Total Gain/Loss",
        title_key="investment_preset.portfolio_gain_stat",
        default_row_span=1, default_col_span=3,
        config={"source": "portfolio_stat", "chart_type": "stat", "metric": "total_gain"},
    ),
    InvestmentPresetDefinition(
        preset_id="portfolio_income_stat", title="Income Received",
        title_key="investment_preset.portfolio_income_stat",
        default_row_span=1, default_col_span=3,
        config={"source": "portfolio_stat", "chart_type": "stat", "metric": "total_income"},
    ),
    InvestmentPresetDefinition(
        preset_id="allocation_by_asset_type", title="Allocation by Asset Type",
        title_key="investment_preset.allocation_by_asset_type",
        default_row_span=3, default_col_span=6,
        config={"source": "allocation", "chart_type": "pie", "dimension": "asset_type", "metric": "market_value"},
    ),
    InvestmentPresetDefinition(
        preset_id="holdings_by_market_value", title="Holdings by Market Value",
        title_key="investment_preset.holdings_by_market_value",
        default_row_span=3, default_col_span=6,
        config={"source": "holdings_breakdown", "chart_type": "bar", "metric": "market_value"},
    ),
    InvestmentPresetDefinition(
        preset_id="portfolio_value_trend", title="Portfolio Value Over Time",
        title_key="investment_preset.portfolio_value_trend",
        default_row_span=3, default_col_span=6,
        config={"source": "portfolio_value", "chart_type": "line"},
    ),
    InvestmentPresetDefinition(
        preset_id="holdings_table", title="Holdings",
        title_key="investment_preset.holdings_table",
        default_row_span=3, default_col_span=6,
        config={"source": "holdings_table", "chart_type": "table"},
    ),
    InvestmentPresetDefinition(
        preset_id="savings_goals", title="Savings Goals",
        title_key="investment_preset.savings_goals",
        default_row_span=3, default_col_span=6,
        config={"source": "savings_goals", "chart_type": "table"},
    ),
    InvestmentPresetDefinition(
        preset_id="projected_annual_income", title="Projected Annual Income",
        title_key="investment_preset.projected_annual_income",
        default_row_span=1, default_col_span=3,
        config={"source": "projected_income", "chart_type": "stat", "period": "annual"},
    ),
    InvestmentPresetDefinition(
        preset_id="projected_value_12m", title="Projected Value (12 months)",
        title_key="investment_preset.projected_value_12m",
        default_row_span=3, default_col_span=6,
        config={"source": "projected_value", "chart_type": "line", "months": 12},
    ),
    InvestmentPresetDefinition(
        preset_id="upcoming_maturities", title="Upcoming Maturities",
        title_key="investment_preset.upcoming_maturities",
        default_row_span=3, default_col_span=6,
        config={"source": "upcoming_maturities", "chart_type": "table"},
    ),
    InvestmentPresetDefinition(
        preset_id="value_at_maturity", title="Value at Maturity",
        title_key="investment_preset.value_at_maturity",
        default_row_span=3, default_col_span=6,
        config={"source": "value_at_maturity", "chart_type": "table"},
    ),
    InvestmentPresetDefinition(
        preset_id="investment_projection", title="Investment Projection",
        title_key="investment_preset.investment_projection",
        default_row_span=4, default_col_span=8,
        config={"source": "projection", "chart_type": "line", "months": 12, "asset_ids": []},
    ),
    InvestmentPresetDefinition(
        preset_id="usd_brl_history", title="USD/BRL",
        title_key="investment_preset.usd_brl_history",
        default_row_span=3, default_col_span=6,
        config={"source": "indicator_history", "chart_type": "line", "indicator_key": "usd_brl"},
    ),
    InvestmentPresetDefinition(
        preset_id="selic_history", title="SELIC",
        title_key="investment_preset.selic_history",
        default_row_span=3, default_col_span=6,
        config={"source": "indicator_history", "chart_type": "line", "indicator_key": "selic"},
    ),
    InvestmentPresetDefinition(
        preset_id="usd_brl_stat", title="USD/BRL",
        title_key="investment_preset.usd_brl_stat",
        default_row_span=1, default_col_span=3,
        config={"source": "indicator_stat", "chart_type": "stat", "indicator_key": "usd_brl"},
    ),
    InvestmentPresetDefinition(
        preset_id="selic_stat", title="SELIC",
        title_key="investment_preset.selic_stat",
        default_row_span=1, default_col_span=3,
        config={"source": "indicator_stat", "chart_type": "stat", "indicator_key": "selic"},
    ),
]

# Widgets seeded onto a brand-new investments dashboard.
DEFAULT_INVESTMENT_LAYOUT = [
    "portfolio_invested_stat",
    "portfolio_market_value_stat",
    "portfolio_gain_stat",
    "portfolio_income_stat",
    "allocation_by_asset_type",
    "holdings_by_market_value",
    "portfolio_value_trend",
    "usd_brl_history",
    "holdings_table",
]


def find_investment_preset(preset_id: str) -> Optional[InvestmentPresetDefinition]:
    return next((p for p in DEFAULT_INVESTMENT_PRESETS if p.preset_id == preset_id), None)


def clone_investment_preset_config(preset: InvestmentPresetDefinition) -> Dict[str, Any]:
    return copy.deepcopy(preset.config)


def default_span_for_source(source: str) -> tuple:
    return (1, 3) if source in ("portfolio_stat", "indicator_stat") else (3, 6)
