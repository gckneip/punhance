from dataclasses import dataclass
from typing import Optional

from src.domain.entities.investment import AssetType


@dataclass
class CreateInvestmentDTO:
    name: str
    asset_type: AssetType
    currency: str = "BRL"
    ticker: Optional[str] = None
    account_id: Optional[str] = None
    current_price: float = 0.0
    goal_amount: Optional[float] = None
    goal_date: Optional[str] = None
    yield_rate: Optional[float] = None
    yield_index: str = "prefixed"
    monthly_contribution: Optional[float] = None
    maturity_date: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


@dataclass
class InvestmentDTO:
    id: str
    name: str
    asset_type: AssetType
    currency: str
    ticker: Optional[str]
    account_id: Optional[str]
    current_price: float
    price_updated_at: Optional[str]
    goal_amount: Optional[float]
    goal_date: Optional[str]
    yield_rate: Optional[float]
    yield_index: str
    monthly_contribution: Optional[float]
    maturity_date: Optional[str]
    is_active: bool
    notes: Optional[str]
    # Derived position fields (from InvestmentService.compute_position) so the
    # table can render without re-invoking the service per row.
    quantity: float
    net_invested: float
    avg_unit_price: float
    market_value: float
    income_total: float
    unrealized_gain: float
    total_return: float
    return_pct: float
    goal_progress_pct: float = 0.0
