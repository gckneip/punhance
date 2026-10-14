from dataclasses import dataclass
from typing import Optional

from src.domain.entities.investment_schedule import ScheduleFrequency


@dataclass
class CreateInvestmentScheduleDTO:
    investment_id: str
    amount: float
    frequency: ScheduleFrequency
    start_date: str
    interval: int = 1
    end_date: Optional[str] = None
    is_active: bool = True


@dataclass
class InvestmentScheduleDTO:
    id: str
    investment_id: str
    amount: float
    frequency: ScheduleFrequency
    start_date: str
    interval: int
    end_date: Optional[str]
    last_generated_date: Optional[str]
    is_active: bool
    next_date: Optional[str] = None  # next upcoming occurrence (computed)
