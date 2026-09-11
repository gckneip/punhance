import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PurchaseItem:
    purchase_id: str
    name: str
    quantity: float = 1.0
    unit: str = "UNIT"
    unit_price: float = 0.0
    total_price: float = 0.0
    category_id: Optional[str] = None
    product_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
