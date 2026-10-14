import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AssetType(Enum):
    RENDA_FIXA = "Renda Fixa"
    RENDA_VARIAVEL_BR = "Renda Variavel BR"
    CRYPTO = "Crypto"
    FOREIGN = "Foreign"
    SAVINGS_BOX = "Savings Box"  # Nubank "Caixinha" / Inter "Cofrinho": a goal-based reserve
    OTHER = "Other"


class YieldIndex(Enum):
    """How a holding's yield_rate is interpreted for income projections."""

    PREFIXED = "prefixed"    # yield_rate is the annual % directly (e.g. 12 -> 12% a.a.)
    CDI = "cdi"              # yield_rate is % of CDI (e.g. 100 -> 100% CDI)
    SELIC = "selic"          # yield_rate is % of the SELIC target
    IPCA_PLUS = "ipca_plus"  # spread added to IPCA (e.g. 5 -> IPCA + 5%)
    SELIC_PLUS = "selic_plus"  # spread added to SELIC (e.g. Tesouro Selic: SELIC + 0.07%)
    CDI_PLUS = "cdi_plus"    # spread added to CDI (e.g. CDI + 2%)


@dataclass
class Investment:
    name: str
    asset_type: AssetType
    currency: str = "BRL"
    ticker: Optional[str] = None
    account_id: Optional[str] = None
    # Manual last-known unit price. For amount-based holdings (e.g. a CDB) where
    # the user only tracks a contributed amount and a current total, quantity is
    # treated as 1 and the current total is stored here (see InvestmentService).
    current_price: float = 0.0
    price_updated_at: Optional[str] = None  # ISO date/datetime string
    # Savings-box goal (Caixinha/Cofrinho): an optional target amount and date.
    goal_amount: Optional[float] = None
    goal_date: Optional[str] = None  # ISO date string
    # Optional yield for income/value projections. yield_rate's meaning depends
    # on yield_index (see YieldIndex). monthly_contribution is a planned recurring
    # deposit used for savings-box goal ETA projections.
    yield_rate: Optional[float] = None
    yield_index: str = "prefixed"
    monthly_contribution: Optional[float] = None
    # Maturity/redemption date for fixed-income titles (e.g. Tesouro Selic 2029).
    maturity_date: Optional[str] = None  # ISO date string
    is_active: bool = True
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
