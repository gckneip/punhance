from dataclasses import dataclass
from typing import Optional

from src.domain.entities.investment_transaction import InvestmentTxnType


@dataclass
class CreateInvestmentTransactionDTO:
    investment_id: str
    txn_type: InvestmentTxnType
    date: str
    quantity: float = 0.0
    unit_price: float = 0.0
    fees: float = 0.0
    total: float = 0.0
    notes: Optional[str] = None


@dataclass
class InvestmentTransactionDTO:
    id: str
    investment_id: str
    txn_type: InvestmentTxnType
    date: str
    quantity: float
    unit_price: float
    fees: float
    total: float
    notes: Optional[str]
