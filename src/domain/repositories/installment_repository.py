from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from src.domain.entities.installment import Installment, InstallmentStatus


class InstallmentRepository(ABC):
    @abstractmethod
    def save(self, installment: Installment, commit: bool = True) -> None:
        pass

    @abstractmethod
    def save_all(self, installments: List[Installment], commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_by_id(self, installment_id: str) -> Optional[Installment]:
        pass

    @abstractmethod
    def find_by_plan(self, plan_id: str) -> List[Installment]:
        pass

    @abstractmethod
    def find_all(
        self,
        status: Optional[InstallmentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Installment]:
        pass

    @abstractmethod
    def find_by_credit_card(self, credit_card_id: str) -> List[Installment]:
        pass

    @abstractmethod
    def delete(self, installment_id: str) -> None:
        pass

    @abstractmethod
    def delete_by_plan(self, plan_id: str, commit: bool = True) -> None:
        pass
