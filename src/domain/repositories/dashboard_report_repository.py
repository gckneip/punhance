from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.dashboard_report import DashboardReport


class DashboardReportRepository(ABC):
    @abstractmethod
    def save(self, report: DashboardReport) -> None:
        pass

    @abstractmethod
    def save_all(self, reports: List[DashboardReport]) -> None:
        pass

    @abstractmethod
    def find_by_id(self, report_id: str) -> Optional[DashboardReport]:
        pass

    @abstractmethod
    def find_all(self) -> List[DashboardReport]:
        pass

    @abstractmethod
    def delete(self, report_id: str) -> None:
        pass
