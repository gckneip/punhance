import uuid
from dataclasses import dataclass, field


@dataclass
class CreditCard:
    name: str
    issuer: str
    credit_limit: float
    closing_day: int
    due_day: int
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
