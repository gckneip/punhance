from enum import Enum


class InvestmentSource(Enum):
    """What an investment widget shows — the top-level selector in the builder."""

    PORTFOLIO_STAT = "portfolio_stat"       # a single portfolio total (stat card)
    ALLOCATION = "allocation"               # holdings grouped by a dimension (pie/bar)
    HOLDINGS_BREAKDOWN = "holdings_breakdown"  # a metric per holding (bar/pie)
    PORTFOLIO_VALUE = "portfolio_value"     # portfolio totals over time (line, needs snapshots)
    INDICATOR_HISTORY = "indicator_history"  # an economic indicator over time (line)
    INDICATOR_STAT = "indicator_stat"       # an indicator's latest value (stat card)
    HOLDINGS_TABLE = "holdings_table"       # a table of all holdings
    SAVINGS_GOALS = "savings_goals"         # progress bars for savings boxes with goals
    PROJECTED_INCOME = "projected_income"   # projected income from yields (stat/bar)
    PROJECTED_VALUE = "projected_value"     # portfolio value projected forward (line)
    UPCOMING_MATURITIES = "upcoming_maturities"  # fixed-income titles by maturity date
    VALUE_AT_MATURITY = "value_at_maturity"      # projected value on each maturity date
    PROJECTION = "projection"                    # interactive per-asset projection (on-screen controls)


class HoldingMetric(Enum):
    MARKET_VALUE = "market_value"
    NET_INVESTED = "net_invested"
    UNREALIZED_GAIN = "unrealized_gain"
    TOTAL_RETURN = "total_return"
    INCOME_TOTAL = "income_total"
    RETURN_PCT = "return_pct"
    QUANTITY = "quantity"


class PortfolioMetric(Enum):
    TOTAL_INVESTED = "total_invested"
    TOTAL_MARKET_VALUE = "total_market_value"
    TOTAL_GAIN = "total_gain"
    TOTAL_INCOME = "total_income"
    RETURN_PCT = "return_pct"


class AllocationDimension(Enum):
    ASSET_TYPE = "asset_type"
    CURRENCY = "currency"


# Portfolio-value-over-time line: which stored snapshot totals to plot.
PORTFOLIO_VALUE_METRICS = (
    PortfolioMetric.TOTAL_MARKET_VALUE,
    PortfolioMetric.TOTAL_INVESTED,
)

# Percentage-valued metrics render with a "%" axis/tooltip rather than currency.
PERCENT_METRICS = {HoldingMetric.RETURN_PCT, PortfolioMetric.RETURN_PCT}
