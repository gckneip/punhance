import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
from enum import Enum


class PaymentMethod(Enum):
    CASH = "cash"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    PIX = "pix"
    BANK_TRANSFER = "bank_transfer"


@dataclass
class Purchase:
    financial_event_id: str
    total_amount: float
    payment_method: PaymentMethod
    credit_card_id: Optional[str] = None
    counterparty_id: Optional[str] = None
    invoice_date: Optional[date] = None
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
