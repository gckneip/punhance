from typing import Optional

from src.presentation.widgets.dashboard.base_dashboard_tabs_widget import BaseDashboardTabsWidget
from src.presentation.widgets.dashboard.dashboard_grid_widget import DashboardGridWidget


class DashboardTabsWidget(BaseDashboardTabsWidget):
    """Finance dashboard: one DashboardGridWidget per report tab."""

    def __init__(
        self,
        dashboard_report_use_cases,
        dashboard_layout_use_cases,
        chart_data_service,
        financial_event_use_cases=None,
        purchase_use_cases=None,
        dashboard_widget_template_use_cases=None,
        parent=None,
    ):
        self._chart_data_service = chart_data_service
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases
        self._last_data_args: Optional[dict] = None
        super().__init__(
            dashboard_report_use_cases,
            dashboard_layout_use_cases,
            dashboard_widget_template_use_cases=dashboard_widget_template_use_cases,
            context="finance",
            parent=parent,
        )

    def _create_grid(self, dashboard_id: str) -> DashboardGridWidget:
        return DashboardGridWidget(
            self._layout_use_cases, self._chart_data_service, self._financial_event_use_cases,
            self._purchase_use_cases, dashboard_id=dashboard_id,
            dashboard_widget_template_use_cases=self._widget_template_use_cases,
        )

    def _refresh_new_grid(self, grid) -> None:
        if self._last_data_args is not None:
            grid.refresh(**self._last_data_args)

    def refresh(
        self, events, accounts=None, categories=None, counterparties=None, purchases=None,
        multi_category_event_ids=None, credit_cards=None, installments_by_event=None,
    ):
        self._last_data_args = dict(
            events=events, accounts=accounts, categories=categories, counterparties=counterparties,
            purchases=purchases, multi_category_event_ids=multi_category_event_ids,
            credit_cards=credit_cards, installments_by_event=installments_by_event,
        )
        for grid in self._grids.values():
            grid.refresh(**self._last_data_args)
