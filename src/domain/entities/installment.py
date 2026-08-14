import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class InstallmentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


@dataclass
class Installment:
    installment_plan_id: str
    installment_number: int
    amount: float
    due_date: date
    status: InstallmentStatus = InstallmentStatus.PENDING
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
