from dataclasses import dataclass
from datetime import date


@dataclass
class InstallmentDTO:
    id: str
    installment_plan_id: str
    installment_number: int
    amount: float
    due_date: date
    status: str
