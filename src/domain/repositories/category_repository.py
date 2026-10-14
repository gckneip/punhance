from abc import ABC, abstractmethod
from typing import List, Optional, Set
from src.domain.entities.category import Category


class CategoryRepository(ABC):
    @abstractmethod
    def save(self, category: Category) -> None:
        pass

    @abstractmethod
    def find_by_id(self, category_id: str) -> Optional[Category]:
        pass

    @abstractmethod
    def find_all(self) -> List[Category]:
        pass

    @abstractmethod
    def find_investment_ids(self) -> Set[str]:
        """Ids of investment-flagged categories plus all their descendants."""
        pass

    @abstractmethod
    def delete(self, category_id: str) -> None:
        pass
