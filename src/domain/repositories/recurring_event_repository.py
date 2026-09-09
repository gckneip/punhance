from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.entities.recurring_event import RecurringEvent


class RecurringEventRepository(ABC):
    @abstractmethod
    def save(self, recurring_event: RecurringEvent, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_by_id(self, recurring_event_id: str) -> Optional[RecurringEvent]:
        pass

    @abstractmethod
    def find_all(self, is_active: Optional[bool] = None) -> List[RecurringEvent]:
        pass

    @abstractmethod
    def delete(self, recurring_event_id: str, commit: bool = True) -> None:
        pass

    @abstractmethod
    def save_skip(self, recurring_event_id: str, occurrence_date: date, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_skips(self, recurring_event_id: str) -> List[date]:
        pass

    @abstractmethod
    def delete_skip(self, recurring_event_id: str, occurrence_date: date, commit: bool = True) -> None:
        pass
