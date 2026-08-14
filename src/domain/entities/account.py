import uuid
from dataclasses import dataclass, field


@dataclass
class Account:
    name: str
    type: str
    initial_balance: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
