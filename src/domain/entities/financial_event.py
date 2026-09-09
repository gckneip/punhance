import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class EventType(Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    PURCHASE = "purchase"
    CARD_PAYMENT = "card_payment"
    LOAN_PAYMENT = "loan_payment"
    INVESTMENT = "investment"
    REFUND = "refund"


@dataclass
class FinancialEvent:
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
    recurring_event_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        now = datetime.now().isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
