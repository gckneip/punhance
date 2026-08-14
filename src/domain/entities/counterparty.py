import uuid
from dataclasses import dataclass, field


@dataclass
class Counterparty:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
