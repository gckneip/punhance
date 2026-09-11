from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date
from src.domain.entities.purchase import PaymentMethod


@dataclass
class CreatePurchaseItemDTO:
    name: str
    quantity: float = 1.0
    unit: str = "UNIT"
    unit_price: float = 0.0
    total_price: float = 0.0
    category_id: Optional[str] = None
    product_id: Optional[str] = None


@dataclass
class CreatePurchaseDTO:
    event_date: date
    description: str
    total_amount: float
    payment_method: PaymentMethod
    credit_card_id: Optional[str] = None
    account_id: Optional[str] = None
    counterparty_id: Optional[str] = None
    notes: Optional[str] = None
    installment_count: int = 1
    remainder_on_first: bool = False
    category_id: Optional[str] = None
    items: List[CreatePurchaseItemDTO] = field(default_factory=list)


@dataclass
class PurchaseItemDTO:
    id: str
    purchase_id: str
    name: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    category_id: Optional[str]
    product_id: Optional[str] = None


@dataclass
class PurchaseDTO:
    id: str
    financial_event_id: str
    total_amount: float
    payment_method: str
    credit_card_id: Optional[str]
    counterparty_id: Optional[str]
    invoice_date: Optional[date]
    notes: Optional[str]
    event_date: Optional[date]
    description: Optional[str]


@dataclass
class InstallmentDTO:
    id: str
    installment_plan_id: str
    installment_number: int
    amount: float
    due_date: date
    status: str
