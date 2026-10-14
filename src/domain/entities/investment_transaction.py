import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InvestmentTxnType(Enum):
    BUY = "Buy"
    SELL = "Sell"
    CONTRIBUTION = "Contribution"
    WITHDRAWAL = "Withdrawal"
    DIVIDEND = "Dividend"
    INTEREST = "Interest"
    FEE = "Fee"
    TAX = "Tax"


# Transaction types that add to / remove from the invested principal and the
# held quantity. Income/cost types (dividend, interest, fee, tax) affect only
# realized income, never quantity or invested basis.
PRINCIPAL_IN_TYPES = (InvestmentTxnType.BUY, InvestmentTxnType.CONTRIBUTION)
PRINCIPAL_OUT_TYPES = (InvestmentTxnType.SELL, InvestmentTxnType.WITHDRAWAL)
INCOME_TYPES = (InvestmentTxnType.DIVIDEND, InvestmentTxnType.INTEREST)
COST_TYPES = (InvestmentTxnType.FEE, InvestmentTxnType.TAX)


@dataclass
class InvestmentTransaction:
    investment_id: str
    txn_type: InvestmentTxnType
    date: str  # ISO date string
    quantity: float = 0.0
    unit_price: float = 0.0
    fees: float = 0.0
    total: float = 0.0
    notes: Optional[str] = None
    # When set, this transaction mirrors a finance investment event and is kept
    # in sync with it (created/edited/deleted together).
    financial_event_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
