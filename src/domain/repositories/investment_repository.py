from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.investment import Investment


class InvestmentRepository(ABC):
    @abstractmethod
    def save(self, investment: Investment) -> None:
        pass

    @abstractmethod
    def find_by_id(self, investment_id: str) -> Optional[Investment]:
        pass

    @abstractmethod
    def find_all(self) -> List[Investment]:
        pass

    @abstractmethod
    def delete(self, investment_id: str) -> None:
        pass
