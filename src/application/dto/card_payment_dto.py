from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class CreateCardPaymentDTO:
    event_date: date
    description: str
    amount: float
    account_id: str
    credit_card_id: str
    installment_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None
