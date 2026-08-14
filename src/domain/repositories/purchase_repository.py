from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.purchase import Purchase
from src.domain.entities.purchase_item import PurchaseItem


class PurchaseRepository(ABC):
    @abstractmethod
    def save(self, purchase: Purchase, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_by_id(self, purchase_id: str) -> Optional[Purchase]:
        pass

    @abstractmethod
    def find_by_financial_event(self, financial_event_id: str) -> Optional[Purchase]:
        pass

    @abstractmethod
    def find_all(self) -> List[Purchase]:
        pass

    @abstractmethod
    def delete(self, purchase_id: str) -> None:
        pass

    @abstractmethod
    def save_item(self, item: PurchaseItem, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_items_by_purchase(self, purchase_id: str) -> List[PurchaseItem]:
        pass

    @abstractmethod
    def delete_items_by_purchase(self, purchase_id: str, commit: bool = True) -> None:
        pass
