import uuid
from dataclasses import dataclass, field


@dataclass
class PortfolioSnapshot:
    """A dated snapshot of the whole investment portfolio's aggregate totals,
    recorded over time so a portfolio-value-over-time chart can be drawn (the
    live positions only ever hold a current value)."""

    date: str  # ISO date string (YYYY-MM-DD); one snapshot per day
    total_invested: float = 0.0
    total_market_value: float = 0.0
    total_gain: float = 0.0
    total_income: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
