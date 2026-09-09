from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.domain.entities.financial_event import EventType
from src.domain.entities.recurring_event import RecurrenceFrequency


@dataclass
class CreateRecurringEventDTO:
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


@dataclass
class RecurringEventDTO:
    id: str
    event_type: str
    description: str
    amount: float
    frequency: str
    interval: int
    day_of_month: Optional[int]
    weekday: Optional[int]
    month: Optional[int]
    start_date: date
    end_date: Optional[date]
    is_active: bool
    category_id: Optional[str]
    account_id: Optional[str]
    destination_account_id: Optional[str]
    credit_card_id: Optional[str]
    counterparty_id: Optional[str]
    currency: str
    notes: Optional[str]


@dataclass
class VirtualOccurrenceDTO:
    """One not-yet-confirmed occurrence of a recurring event. Shaped to drop
    directly into EventDialog(event=...) unmodified (event_type as str,
    event_date == occurrence_date)."""
    recurring_event_id: str
    occurrence_date: date
    event_type: str
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
