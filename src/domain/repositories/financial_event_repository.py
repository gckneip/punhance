from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from src.domain.entities.financial_event import FinancialEvent, EventType


class FinancialEventRepository(ABC):
    @abstractmethod
    def save(self, event: FinancialEvent, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_by_id(self, event_id: str) -> Optional[FinancialEvent]:
        pass

    @abstractmethod
    def find_by_ids(self, event_ids: List[str]) -> List[FinancialEvent]:
        pass

    @abstractmethod
    def find_all(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        event_type: Optional[EventType] = None,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
        destination_account_id: Optional[str] = None,
        counterparty_id: Optional[str] = None,
        description: Optional[str] = None,
        recurring_event_id: Optional[str] = None,
    ) -> List[FinancialEvent]:
        pass

    @abstractmethod
    def delete(self, event_id: str) -> None:
        pass
