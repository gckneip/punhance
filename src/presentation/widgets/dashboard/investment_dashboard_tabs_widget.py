from src.presentation.widgets.dashboard.base_dashboard_tabs_widget import BaseDashboardTabsWidget
from src.presentation.widgets.dashboard.investment_grid_widget import InvestmentGridWidget


class InvestmentDashboardTabsWidget(BaseDashboardTabsWidget):
    """Customizable investments analytics dashboard (the "Painel" tab).

    Holdings management and economic-indicator refresh now live in their own
    dedicated tabs (Carteira / Indicadores), so this widget is purely the
    multi-report analytics grid.
    """

    def __init__(
        self,
        dashboard_report_use_cases,
        dashboard_layout_use_cases,
        investment_chart_data_service,
        dashboard_widget_template_use_cases=None,
        parent=None,
    ):
        self._service = investment_chart_data_service
        super().__init__(
            dashboard_report_use_cases,
            dashboard_layout_use_cases,
            dashboard_widget_template_use_cases=dashboard_widget_template_use_cases,
            context="investments",
            parent=parent,
        )

    def _create_grid(self, dashboard_id: str) -> InvestmentGridWidget:
        return InvestmentGridWidget(
            self._layout_use_cases, self._service, dashboard_id=dashboard_id,
            dashboard_widget_template_use_cases=self._widget_template_use_cases,
        )

    def _refresh_new_grid(self, grid) -> None:
        grid.refresh()

    def refresh(self):
        for grid in self._grids.values():
            grid.refresh()
