from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.counterparty import Counterparty


class CounterpartyRepository(ABC):
    @abstractmethod
    def save(self, counterparty: Counterparty) -> None:
        pass

    @abstractmethod
    def find_by_id(self, counterparty_id: str) -> Optional[Counterparty]:
        pass

    @abstractmethod
    def find_all(self) -> List[Counterparty]:
        pass

    @abstractmethod
    def delete(self, counterparty_id: str) -> None:
        pass
