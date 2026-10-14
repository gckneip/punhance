from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.investment_schedule import InvestmentSchedule


class InvestmentScheduleRepository(ABC):
    @abstractmethod
    def save(self, schedule: InvestmentSchedule) -> None:
        pass

    @abstractmethod
    def find_by_id(self, schedule_id: str) -> Optional[InvestmentSchedule]:
        pass

    @abstractmethod
    def find_by_investment(self, investment_id: str) -> List[InvestmentSchedule]:
        pass

    @abstractmethod
    def find_all_active(self) -> List[InvestmentSchedule]:
        pass

    @abstractmethod
    def delete(self, schedule_id: str) -> None:
        pass

    @abstractmethod
    def delete_by_investment(self, investment_id: str) -> None:
        pass
