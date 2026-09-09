import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from src.domain.entities.financial_event import EventType


class RecurrenceFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class RecurringEvent:
    event_type: EventType
    description: str
    amount: float
    frequency: RecurrenceFrequency
    start_date: date
    interval: int = 1
    day_of_month: Optional[int] = None
    weekday: Optional[int] = None
    month: Optional[int] = None
    end_date: Optional[date] = None
    is_active: bool = True
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    counterparty_id: Optional[str] = None
    currency: str = "BRL"
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        now = datetime.now().isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now


@dataclass
class RecurringEventSkip:
    recurring_event_id: str
    occurrence_date: date
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
