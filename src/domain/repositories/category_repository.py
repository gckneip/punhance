from abc import ABC, abstractmethod
from typing import List, Optional
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
    def delete(self, category_id: str) -> None:
        pass
