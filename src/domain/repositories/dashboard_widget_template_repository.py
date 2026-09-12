from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.dashboard_widget_template import DashboardWidgetTemplate


class DashboardWidgetTemplateRepository(ABC):
    @abstractmethod
    def save(self, template: DashboardWidgetTemplate) -> None:
        pass

    @abstractmethod
    def find_by_id(self, template_id: str) -> Optional[DashboardWidgetTemplate]:
        pass

    @abstractmethod
    def find_all(self) -> List[DashboardWidgetTemplate]:
        pass

    @abstractmethod
    def delete(self, template_id: str) -> None:
        pass
