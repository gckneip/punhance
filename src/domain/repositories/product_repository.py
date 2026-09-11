from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    def save(self, product: Product) -> None:
        pass

    @abstractmethod
    def find_by_id(self, product_id: str) -> Optional[Product]:
        pass

    @abstractmethod
    def find_all(self) -> List[Product]:
        pass

    @abstractmethod
    def delete(self, product_id: str) -> None:
        pass
