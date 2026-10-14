from typing import Optional

from PySide6.QtWidgets import QWidget

from src.presentation.labels import localize_default_title
from src.presentation.widgets.dashboard.base_grid_widget import BaseGridWidget
from src.presentation.widgets.dashboard.investment_widget_renderer import build_investment_content
from src.presentation.widgets.dashboard.investment_projection_widget import InvestmentProjectionWidget
from src.domain.services.investment_chart_types import InvestmentSource


class InvestmentGridWidget(BaseGridWidget):
    """Customizable investments dashboard grid: allocation/holdings/portfolio/
    indicator widgets. Pulls data straight from InvestmentChartDataService."""

    def __init__(
        self,
        dashboard_layout_use_cases,
        investment_chart_data_service,
        dashboard_id="investments_default",
        dashboard_widget_template_use_cases=None,
        parent=None,
    ):
        super().__init__(
            dashboard_layout_use_cases,
            dashboard_id=dashboard_id,
            dashboard_widget_template_use_cases=dashboard_widget_template_use_cases,
            parent=parent,
        )
        self._service = investment_chart_data_service

    def refresh(self):
        self._load_widgets()
        if not self._frames:
            self._rebuild_layout()
        else:
            self._push_data()

    def _build_content(self, dto) -> QWidget:
        # The projection widget is interactive: its on-screen period/asset
        # controls persist back into the widget config.
        if dto.config.get("source") == InvestmentSource.PROJECTION.value:
            return InvestmentProjectionWidget(
                self._service, dto.config,
                on_config_change=lambda cfg, wid=dto.id: self._persist_config(wid, cfg),
            )
        return build_investment_content(
            localize_default_title(dto.title, dto.config), dto.config, self._service
        )

    def _persist_config(self, widget_id: str, config: dict) -> None:
        self._layout_use_cases.update_widget_config(widget_id, config)
        for w in self._widgets:
            if w.id == widget_id:
                w.config = config

    def _push_data(self):
        for dto in self._widgets:
            frame = self._frames.get(dto.id)
            if frame is None:
                continue
            frame.set_content(self._build_content(dto))

    def _open_add_widget_dialog(self) -> Optional[dict]:
        from src.presentation.dialogs.investment_widget_picker_dialog import InvestmentWidgetPickerDialog

        dialog = InvestmentWidgetPickerDialog(
            self, service=self._service,
            dashboard_widget_template_use_cases=self._widget_template_use_cases,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog.get_data()
