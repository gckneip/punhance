from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple
from src.domain.entities.purchase import Purchase
from src.domain.entities.purchase_item import PurchaseItem


@dataclass
class ProductPurchaseRecord:
    """One line item of a catalogued product, flattened with the date and
    store of the purchase it belongs to. Returned by
    :meth:`PurchaseRepository.find_product_purchase_history` to feed the
    shopping-suggestion engine without issuing one query per item."""
    product_id: str
    event_date: date
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    counterparty_id: Optional[str]


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
    def find_items_in_range(self, date_from=None, date_to=None) -> List[PurchaseItem]:
        pass

    @abstractmethod
    def count_items_by_product(self, product_id: str) -> int:
        pass

    @abstractmethod
    def find_items_by_product(self, product_id: str, limit: Optional[int] = None) -> List[PurchaseItem]:
        pass

    @abstractmethod
    def delete_items_by_purchase(self, purchase_id: str, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_product_prices_with_counterparty(self) -> List[Tuple[str, float, Optional[str]]]:
        pass

    @abstractmethod
    def find_product_purchase_history(self) -> List[ProductPurchaseRecord]:
        pass
