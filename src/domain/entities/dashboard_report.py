import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DashboardReport:
    name: str
    sort_order: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        now = datetime.now().isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
