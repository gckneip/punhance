import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ScheduleFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class InvestmentSchedule:
    """A recurring planned contribution into an investment (e.g. R$200/month).

    Past-due occurrences are materialized as real CONTRIBUTION transactions
    (see InvestmentUseCases.generate_due_schedules); future occurrences feed the
    projection charts.
    """

    investment_id: str
    amount: float
    frequency: ScheduleFrequency
    start_date: str  # ISO date
    interval: int = 1
    end_date: Optional[str] = None  # ISO date
    last_generated_date: Optional[str] = None  # ISO date watermark
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
