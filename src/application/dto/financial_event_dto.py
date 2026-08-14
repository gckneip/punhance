from dataclasses import dataclass
from typing import Optional
from datetime import date
from src.domain.entities.financial_event import EventType


@dataclass
class CreateFinancialEventDTO:
    event_type: EventType
    event_date: date
    description: str
    amount: float
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    counterparty_id: Optional[str] = None
    currency: str = "BRL"
    notes: Optional[str] = None


@dataclass
class FinancialEventDTO:
    id: str
    event_type: str
    event_date: date
    description: str
    amount: float
    category_id: Optional[str]
    account_id: Optional[str]
    destination_account_id: Optional[str]
    credit_card_id: Optional[str]
    counterparty_id: Optional[str]
    currency: str
    notes: Optional[str]
    created_at: str
    updated_at: str
