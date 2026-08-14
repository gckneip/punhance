from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.account import Account


class AccountRepository(ABC):
    @abstractmethod
    def save(self, account: Account) -> None:
        pass

    @abstractmethod
    def find_by_id(self, account_id: str) -> Optional[Account]:
        pass

    @abstractmethod
    def find_all(self) -> List[Account]:
        pass

    @abstractmethod
    def delete(self, account_id: str) -> None:
        pass
