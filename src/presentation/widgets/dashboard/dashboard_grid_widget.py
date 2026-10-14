from typing import Dict, Optional

from PySide6.QtWidgets import QLabel, QWidget

from src.domain.services.chart_data_service import DateRangeSpec, GroupByDimension, MetricType
from src.presentation.labels import localize_default_title
from src.presentation.widgets.dashboard.base_grid_widget import (
    BaseGridWidget,
    # re-exported for backward compatibility with existing importers
    GRID_COLUMNS, GRID_SPACING, ROW_UNIT_PX,
    find_next_placement, _fits, _occupied_cells, _footprints_overlap,
)
from src.presentation.widgets.dashboard.builtin_widgets import (
    EventsTableWidget, QuickAddBarWidget, SavingsRateStatWidget, split_event_rows,
)
from src.presentation.widgets.dashboard.generic_widget_renderer import (
    build_generic_content, widget_supports_date_range, widget_supports_period_ahead,
)


class DashboardGridWidget(BaseGridWidget):
    """Finance dashboard grid: transactions/accounts/cards widgets + builtins,
    with per-widget date-range / period-ahead header selectors."""

    def __init__(
        self,
        dashboard_layout_use_cases,
        chart_data_service,
        financial_event_use_cases=None,
        purchase_use_cases=None,
        dashboard_id="default",
        dashboard_widget_template_use_cases=None,
        parent=None,
    ):
        super().__init__(
            dashboard_layout_use_cases,
            dashboard_id=dashboard_id,
            dashboard_widget_template_use_cases=dashboard_widget_template_use_cases,
            parent=parent,
        )
        self._chart_data_service = chart_data_service
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases

        self._builtin_content: Dict[str, QWidget] = {}
        self._last_data_args: Optional[dict] = None
        # Session-only per-widget date-range overrides from the frame header
        # selector - deliberately not persisted, so widgets keep their
        # configured default range across restarts (see WidgetFrame).
        self._date_range_overrides: Dict[str, dict] = {}
        # Same idea as above, for the "how far into the future" selector on
        # upcoming-events/-installments/-recurring table widgets.
        self._days_ahead_overrides: Dict[str, int] = {}

    def focus_quick_add(self):
        for content in self._builtin_content.values():
            if isinstance(content, QuickAddBarWidget):
                content.focus()
                return

    def refresh(
        self, events, accounts=None, categories=None, counterparties=None, purchases=None,
        multi_category_event_ids=None, credit_cards=None, installments_by_event=None,
    ):
        self._last_data_args = dict(
            events=events, accounts=accounts, categories=categories, counterparties=counterparties,
            purchases=purchases, multi_category_event_ids=multi_category_event_ids,
            credit_cards=credit_cards, installments_by_event=installments_by_event,
        )
        self._load_widgets()
        if not self._frames:
            self._rebuild_layout()
        else:
            self._push_data()

    # -- subclass seams -------------------------------------------------------

    def _before_rebuild(self):
        self._builtin_content.clear()

    def _build_content(self, dto) -> QWidget:
        if dto.kind == "builtin":
            content = self._build_builtin_content(dto)
            self._builtin_content[dto.id] = content
            return content
        return build_generic_content(
            localize_default_title(dto.title, dto.config), self._effective_config(dto), self._chart_data_service
        )

    def _frame_date_range(self, dto):
        if dto.kind != "builtin" and widget_supports_date_range(dto.config):
            return self._effective_config(dto).get("date_range")
        return None

    def _frame_days_ahead(self, dto):
        if dto.kind != "builtin" and widget_supports_period_ahead(dto.config):
            return self._effective_config(dto).get("days_ahead")
        return None

    def _effective_config(self, dto) -> dict:
        """dto.config with any live (session-only) date-range/days-ahead
        overrides from the widget's header selectors applied on top."""
        config = dto.config
        date_override = self._date_range_overrides.get(dto.id)
        days_override = self._days_ahead_overrides.get(dto.id)
        if date_override is None and days_override is None:
            return config

        result = config
        if date_override is not None and widget_supports_date_range(config):
            result = {**result, "date_range": date_override}
        if days_override is not None and widget_supports_period_ahead(config):
            result = {**result, "days_ahead": days_override}
        return result

    def _build_builtin_content(self, dto) -> QWidget:
        key = dto.config.get("builtin_key")
        if key == "quick_add_bar":
            widget = QuickAddBarWidget(self._financial_event_use_cases)
            widget.entry_added.connect(self.entry_added.emit)
            return widget
        if key in ("recent_events", "future_transactions"):
            mode = "recent" if key == "recent_events" else "future"
            widget = EventsTableWidget(mode, self._financial_event_use_cases, self._purchase_use_cases)
            widget.entry_added.connect(self.entry_added.emit)
            widget.edit_event_requested.connect(self.edit_event_requested.emit)
            return widget
        if key == "savings_rate_stat":
            return SavingsRateStatWidget()
        from src.presentation.i18n import t
        return QLabel(t("dashboard.unknown_builtin", key=key))

    # -- data refresh (no structural change) ----------------------------------

    def _push_data(self):
        if self._last_data_args is None:
            return
        args = self._last_data_args
        recent_rows, future_rows = split_event_rows(
            args["events"], args["accounts"], args["categories"], args["purchases"],
            args["multi_category_event_ids"], args["credit_cards"], args["installments_by_event"],
        )

        savings_summary = None
        for dto in self._widgets:
            frame = self._frames.get(dto.id)
            if frame is None:
                continue
            if dto.kind == "builtin":
                content = self._builtin_content.get(dto.id)
                key = dto.config.get("builtin_key")
                if key == "quick_add_bar":
                    content.set_options(args["accounts"], args["categories"], args["credit_cards"])
                elif key == "recent_events":
                    content.set_rows(recent_rows)
                elif key == "future_transactions":
                    content.set_rows(future_rows)
                elif key == "savings_rate_stat":
                    if savings_summary is None:
                        month = DateRangeSpec(mode="calendar", period="month", offset=0)
                        income = self._chart_data_service.get_stat(MetricType.INCOME, month)
                        invested = self._chart_data_service.get_invested(month)
                        savings_summary = {"income": income, "invested": invested}
                    content.set_rate(
                        savings_summary.get("income", 0.0), savings_summary.get("invested", 0.0)
                    )
            else:
                frame.set_content(
                    build_generic_content(localize_default_title(dto.title, dto.config), self._effective_config(dto), self._chart_data_service)
                )

    # -- date-range / period-ahead header selectors ---------------------------

    def _on_widget_date_range_changed(self, widget_id: str, date_range: dict):
        self._date_range_overrides[widget_id] = date_range
        dto = next((w for w in self._widgets if w.id == widget_id), None)
        frame = self._frames.get(widget_id)
        if dto is None or frame is None:
            return
        frame.set_content(build_generic_content(localize_default_title(dto.title, dto.config), self._effective_config(dto), self._chart_data_service))

    def _on_widget_days_ahead_changed(self, widget_id: str, days_ahead: int):
        self._days_ahead_overrides[widget_id] = days_ahead
        dto = next((w for w in self._widgets if w.id == widget_id), None)
        frame = self._frames.get(widget_id)
        if dto is None or frame is None:
            return
        frame.set_content(build_generic_content(localize_default_title(dto.title, dto.config), self._effective_config(dto), self._chart_data_service))

    # -- add-widget picker ----------------------------------------------------

    def _open_add_widget_dialog(self) -> Optional[dict]:
        from src.presentation.dialogs.dashboard_widget_picker_dialog import DashboardWidgetPickerDialog

        dialog = DashboardWidgetPickerDialog(
            self, accounts=(self._last_data_args or {}).get("accounts") or [],
            categories=(self._last_data_args or {}).get("categories") or [],
            counterparties=(self._last_data_args or {}).get("counterparties") or [],
            credit_cards=(self._last_data_args or {}).get("credit_cards") or [],
            chart_data_service=self._chart_data_service,
            dashboard_widget_template_use_cases=self._widget_template_use_cases,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog.get_data()
