from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.investment_transaction import InvestmentTransaction


class InvestmentTransactionRepository(ABC):
    @abstractmethod
    def save(self, transaction: InvestmentTransaction) -> None:
        pass

    @abstractmethod
    def find_by_id(self, transaction_id: str) -> Optional[InvestmentTransaction]:
        pass

    @abstractmethod
    def find_by_investment(self, investment_id: str) -> List[InvestmentTransaction]:
        pass

    @abstractmethod
    def delete(self, transaction_id: str) -> None:
        pass

    @abstractmethod
    def delete_by_investment(self, investment_id: str) -> None:
        pass

    @abstractmethod
    def find_by_financial_event(self, financial_event_id: str) -> Optional[InvestmentTransaction]:
        pass

    @abstractmethod
    def delete_by_financial_event(self, financial_event_id: str) -> None:
        pass
