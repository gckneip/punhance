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


# Expense-like events that can be charged directly to a credit card instead
# of to a bank account. (CARD_PAYMENT is excluded: it is the bill payment
# itself and always leaves a real account.)
_CARD_CHARGEABLE_EXPENSE_TYPES = frozenset({
    EventType.EXPENSE, EventType.PURCHASE,
    EventType.LOAN_PAYMENT, EventType.INVESTMENT,
})


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

    @property
    def is_uncleared_card_charge(self) -> bool:
        """True for an expense charged to a credit card whose bill has not been
        paid yet. Such a charge is not a real account outflow - it becomes one
        only when the card bill is paid (a CARD_PAYMENT event against a real
        account). Reconciliation totals must skip it to avoid double-counting
        the same spend (the charge plus its later payment)."""
        return (
            self.credit_card_id is not None
            and self.event_type in _CARD_CHARGEABLE_EXPENSE_TYPES
        )
