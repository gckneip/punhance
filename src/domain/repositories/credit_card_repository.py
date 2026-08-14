from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.credit_card import CreditCard


class CreditCardRepository(ABC):
    @abstractmethod
    def save(self, card: CreditCard) -> None:
        pass

    @abstractmethod
    def find_by_id(self, card_id: str) -> Optional[CreditCard]:
        pass

    @abstractmethod
    def find_all(self) -> List[CreditCard]:
        pass

    @abstractmethod
    def delete(self, card_id: str) -> None:
        pass
