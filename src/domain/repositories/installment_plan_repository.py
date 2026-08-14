from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.installment_plan import InstallmentPlan


class InstallmentPlanRepository(ABC):
    @abstractmethod
    def save(self, plan: InstallmentPlan, commit: bool = True) -> None:
        pass

    @abstractmethod
    def find_by_id(self, plan_id: str) -> Optional[InstallmentPlan]:
        pass

    @abstractmethod
    def find_by_purchase(self, purchase_id: str) -> Optional[InstallmentPlan]:
        pass

    @abstractmethod
    def find_all(self) -> List[InstallmentPlan]:
        pass

    @abstractmethod
    def delete(self, plan_id: str, commit: bool = True) -> None:
        pass
