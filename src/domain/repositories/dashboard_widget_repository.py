from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.dashboard_widget import DashboardWidget


class DashboardWidgetRepository(ABC):
    @abstractmethod
    def save(self, widget: DashboardWidget) -> None:
        pass

    @abstractmethod
    def save_all(self, widgets: List[DashboardWidget]) -> None:
        pass

    @abstractmethod
    def find_by_id(self, widget_id: str) -> Optional[DashboardWidget]:
        pass

    @abstractmethod
    def find_all(self, dashboard_id: str = "default") -> List[DashboardWidget]:
        pass

    @abstractmethod
    def delete(self, widget_id: str) -> None:
        pass
