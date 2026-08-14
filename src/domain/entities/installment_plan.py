import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class InstallmentPlan:
    purchase_id: str
    total_amount: float
    installment_count: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
