from typing import List, Optional
from src.domain.entities.dashboard_report import DashboardReport
from src.domain.repositories.dashboard_report_repository import DashboardReportRepository
from src.domain.repositories.dashboard_widget_repository import DashboardWidgetRepository
from src.application.dto.dashboard_report_dto import DashboardReportDTO


class DashboardReportUseCases:
    def __init__(
        self,
        dashboard_report_repository: DashboardReportRepository,
        dashboard_widget_repository: DashboardWidgetRepository,
    ):
        self._repo = dashboard_report_repository
        self._widget_repo = dashboard_widget_repository

    def list_reports(self) -> List[DashboardReportDTO]:
        return [self._to_dto(r) for r in self._repo.find_all()]

    def create_report(self, name: str) -> DashboardReportDTO:
        entity = DashboardReport(name=name, sort_order=len(self._repo.find_all()))
        self._repo.save(entity)
        return self._to_dto(entity)

    def rename_report(self, report_id: str, name: str) -> Optional[DashboardReportDTO]:
        entity = self._repo.find_by_id(report_id)
        if entity is None:
            return None
        entity.name = name
        self._repo.save(entity)
        return self._to_dto(entity)

    def reorder_reports(self, ids_in_order: List[str]) -> None:
        reports = {r.id: r for r in self._repo.find_all()}
        updated = []
        for index, report_id in enumerate(ids_in_order):
            report = reports.get(report_id)
            if report is None:
                continue
            report.sort_order = index
            updated.append(report)
        self._repo.save_all(updated)

    def delete_report(self, report_id: str) -> None:
        self._widget_repo.delete_by_dashboard_id(report_id)
        self._repo.delete(report_id)

    def seed_default_if_empty(self) -> None:
        if self._repo.find_all():
            return
        self._repo.save(DashboardReport(id="default", name="Dashboard", sort_order=0))

    def _to_dto(self, entity: DashboardReport) -> DashboardReportDTO:
        return DashboardReportDTO(id=entity.id, name=entity.name, sort_order=entity.sort_order)
