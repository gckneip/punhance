from typing import List
from src.domain.entities.dashboard_widget_template import DashboardWidgetTemplate
from src.domain.repositories.dashboard_widget_template_repository import DashboardWidgetTemplateRepository
from src.application.dto.dashboard_widget_template_dto import (
    CreateDashboardWidgetTemplateDTO, DashboardWidgetTemplateDTO,
)


class DashboardWidgetTemplateUseCases:
    def __init__(self, dashboard_widget_template_repository: DashboardWidgetTemplateRepository):
        self._repo = dashboard_widget_template_repository

    def list_templates(self) -> List[DashboardWidgetTemplateDTO]:
        return [self._to_dto(t) for t in self._repo.find_all()]

    def create_template(self, dto: CreateDashboardWidgetTemplateDTO) -> DashboardWidgetTemplateDTO:
        entity = DashboardWidgetTemplate(
            title=dto.title, config=dto.config, row_span=dto.row_span, col_span=dto.col_span,
        )
        self._repo.save(entity)
        return self._to_dto(entity)

    def delete_template(self, template_id: str) -> None:
        self._repo.delete(template_id)

    def _to_dto(self, entity: DashboardWidgetTemplate) -> DashboardWidgetTemplateDTO:
        return DashboardWidgetTemplateDTO(
            id=entity.id, title=entity.title, config=entity.config,
            row_span=entity.row_span, col_span=entity.col_span,
        )
