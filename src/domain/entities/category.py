import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Category:
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None
    # Marks a category (and its sub-categories) as investment-like: events in it
    # are excluded from income/expense totals and category charts, and only move
    # account balances — the same treatment as investment/transfer events.
    is_investment: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
