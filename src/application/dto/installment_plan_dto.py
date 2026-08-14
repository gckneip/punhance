from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateInstallmentPlanDTO:
    purchase_id: str
    total_amount: float
    installment_count: int


@dataclass
class InstallmentPlanDTO:
    id: str
    purchase_id: str
    total_amount: float
    installment_count: int
    created_at: Optional[str]
