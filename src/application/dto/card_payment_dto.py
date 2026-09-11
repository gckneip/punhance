from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class CreateCardPaymentDTO:
    event_date: date
    description: str
    amount: float
    account_id: str
    credit_card_id: str
    notes: Optional[str] = None
