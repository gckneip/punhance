from typing import List
from src.domain.entities.dashboard_widget import DashboardWidget, DashboardWidgetKind
from src.domain.repositories.dashboard_widget_repository import DashboardWidgetRepository
from src.application.dto.dashboard_widget_dto import (
    CreateDashboardWidgetDTO,
    DashboardWidgetDTO,
    DashboardWidgetLayoutUpdateDTO,
)


class DashboardLayoutUseCases:
    def __init__(self, dashboard_widget_repository: DashboardWidgetRepository):
        self._repo = dashboard_widget_repository

    def list_widgets(self, dashboard_id: str = "default") -> List[DashboardWidgetDTO]:
        entities = self._repo.find_all(dashboard_id)
        return [self._to_dto(e) for e in entities]

    def add_widget(self, dto: CreateDashboardWidgetDTO) -> DashboardWidgetDTO:
        entity = DashboardWidget(
            kind=DashboardWidgetKind(dto.kind),
            title=dto.title,
            grid_row=dto.grid_row,
            grid_col=dto.grid_col,
            grid_row_span=dto.grid_row_span,
            grid_col_span=dto.grid_col_span,
            sort_order=dto.sort_order,
            config=dto.config,
            source_preset_id=dto.source_preset_id,
            dashboard_id=dto.dashboard_id,
        )
        self._repo.save(entity)
        return self._to_dto(entity)

    def update_widget_config(self, widget_id: str, config: dict) -> DashboardWidgetDTO:
        entity = self._repo.find_by_id(widget_id)
        if entity is None:
            return None
        entity.config = config
        self._repo.save(entity)
        return self._to_dto(entity)

    def update_layout(self, updates: List[DashboardWidgetLayoutUpdateDTO]) -> None:
        widgets = []
        for update in updates:
            entity = self._repo.find_by_id(update.id)
            if entity is None:
                continue
            entity.grid_row = update.grid_row
            entity.grid_col = update.grid_col
            entity.grid_row_span = update.grid_row_span
            entity.grid_col_span = update.grid_col_span
            entity.sort_order = update.sort_order
            widgets.append(entity)
        self._repo.save_all(widgets)

    def delete_widget(self, widget_id: str) -> None:
        self._repo.delete(widget_id)

    def seed_default_layout_if_empty(self, dashboard_id: str = "default") -> None:
        if self._repo.find_all(dashboard_id):
            return

        def stat(title, metric, sort_order):
            return DashboardWidget(
                kind=DashboardWidgetKind.GENERIC,
                title=title,
                grid_row=1,
                grid_col=sort_order * 3,
                grid_row_span=1,
                grid_col_span=3,
                sort_order=sort_order,
                config={
                    "chart_type": "stat",
                    "metrics": [metric],
                    "group_by": "none",
                    "date_range": {"mode": "calendar", "period": "month", "offset": 0},
                    "filters": {},
                },
                dashboard_id=dashboard_id,
            )

        default_widgets = [
            DashboardWidget(
                kind=DashboardWidgetKind.BUILTIN,
                title="Quick Add",
                grid_row=0,
                grid_col=0,
                grid_row_span=1,
                grid_col_span=12,
                sort_order=0,
                config={"builtin_key": "quick_add_bar"},
                dashboard_id=dashboard_id,
            ),
            stat("Monthly Income", "income", 0),
            stat("Monthly Expenses", "expenses", 1),
            stat("Monthly Net", "net", 2),
            DashboardWidget(
                kind=DashboardWidgetKind.BUILTIN,
                title="Savings Rate",
                grid_row=1,
                grid_col=9,
                grid_row_span=1,
                grid_col_span=3,
                sort_order=3,
                config={"builtin_key": "savings_rate_stat"},
                dashboard_id=dashboard_id,
            ),
            DashboardWidget(
                kind=DashboardWidgetKind.BUILTIN,
                title="Recent Events",
                grid_row=2,
                grid_col=0,
                grid_row_span=3,
                grid_col_span=12,
                sort_order=4,
                config={"builtin_key": "recent_events"},
                dashboard_id=dashboard_id,
            ),
            DashboardWidget(
                kind=DashboardWidgetKind.BUILTIN,
                title="Future Transactions",
                grid_row=5,
                grid_col=0,
                grid_row_span=3,
                grid_col_span=12,
                sort_order=5,
                config={"builtin_key": "future_transactions"},
                dashboard_id=dashboard_id,
            ),
        ]
        self._repo.save_all(default_widgets)

    def _to_dto(self, entity: DashboardWidget) -> DashboardWidgetDTO:
        return DashboardWidgetDTO(
            id=entity.id,
            dashboard_id=entity.dashboard_id,
            kind=entity.kind.value,
            title=entity.title,
            grid_row=entity.grid_row,
            grid_col=entity.grid_col,
            grid_row_span=entity.grid_row_span,
            grid_col_span=entity.grid_col_span,
            sort_order=entity.sort_order,
            config=entity.config,
            source_preset_id=entity.source_preset_id,
        )
