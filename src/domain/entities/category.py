import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Category:
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
