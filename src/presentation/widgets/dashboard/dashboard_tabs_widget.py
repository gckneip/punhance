from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QInputDialog, QMenu, QMessageBox, QTabWidget, QVBoxLayout, QWidget,
)

from src.presentation.widgets.dashboard.dashboard_grid_widget import DashboardGridWidget


class DashboardTabsWidget(QWidget):
    """Hosts one DashboardGridWidget per user-defined "report", switchable via a
    QTabWidget - add/rename/delete/reorder reports, each with its own independent
    widget layout (scoped by dashboard_id)."""

    entry_added = Signal()
    edit_event_requested = Signal(str)

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
        super().__init__(parent)
        self._report_use_cases = dashboard_report_use_cases
        self._layout_use_cases = dashboard_layout_use_cases
        self._chart_data_service = chart_data_service
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases
        self._widget_template_use_cases = dashboard_widget_template_use_cases
        self._grids: Dict[str, DashboardGridWidget] = {}
        self._last_data_args: Optional[dict] = None
        self._last_real_index = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setMovable(True)
        self._tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        self._tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self._tabs.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)
        self._tabs.tabBarDoubleClicked.connect(self._rename_tab)
        self._tabs.currentChanged.connect(self._on_current_changed)

        layout.addWidget(self._tabs)

        # A permanent "+" tab pinned to the end of the tab bar (Chrome-style) -
        # sits right next to the last report tab, so it's easy to spot instead
        # of being stranded in the widget's far corner.
        self._add_tab_placeholder = QWidget()

        for report in self._report_use_cases.list_reports():
            self._add_tab_for_report(report.id, report.name)
        self._append_add_tab()

    # -- report id <-> tab plumbing ------------------------------------------

    def _append_add_tab(self):
        # Plain text, not an icon: Qt only centers a tab's TEXT (AlignCenter)
        # - a tab icon is always laid out flush against the left padding
        # edge regardless of centering intent, which read as off-center.
        # Text also renders through the exact same QTabBar::tab paint path
        # as every real report tab, so it's an exact fit with one border.
        index = self._tabs.addTab(self._add_tab_placeholder, "+")
        self._tabs.setTabToolTip(index, "Add report")

    def _add_tab_for_report(self, dashboard_id: str, name: str) -> int:
        grid = DashboardGridWidget(
            self._layout_use_cases, self._chart_data_service, self._financial_event_use_cases,
            self._purchase_use_cases, dashboard_id=dashboard_id,
            dashboard_widget_template_use_cases=self._widget_template_use_cases,
        )
        grid.entry_added.connect(self.entry_added.emit)
        grid.edit_event_requested.connect(self.edit_event_requested.emit)
        self._grids[dashboard_id] = grid
        if self._last_data_args is not None:
            grid.refresh(**self._last_data_args)
        add_index = self._tabs.indexOf(self._add_tab_placeholder)
        insert_at = add_index if add_index >= 0 else self._tabs.count()
        return self._tabs.insertTab(insert_at, grid, name)

    def _report_id_for_index(self, index: int) -> Optional[str]:
        widget = self._tabs.widget(index)
        for dashboard_id, grid in self._grids.items():
            if grid is widget:
                return dashboard_id
        return None

    def _is_add_tab(self, index: int) -> bool:
        return self._tabs.widget(index) is self._add_tab_placeholder

    # -- public interface (mirrors the old DashboardGridWidget) --------------

    def focus_quick_add(self):
        current = self._tabs.currentWidget()
        if current is not None and current is not self._add_tab_placeholder:
            current.focus_quick_add()

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

    # -- add / rename / delete / reorder ---------------------------------------

    def _on_current_changed(self, index: int):
        if index < 0:
            return
        if self._is_add_tab(index):
            # Defer past this click's own selection handling - reverting
            # immediately here can get overwritten by Qt's own follow-up
            # tab-selection commit, which is what let a cancel leave the
            # (empty) add tab showing instead of bouncing back.
            QTimer.singleShot(0, self._recover_from_add_tab)
            return
        self._last_real_index = index

    def _recover_from_add_tab(self):
        self._tabs.setCurrentIndex(self._last_real_index)
        self._on_add_report()

    def _on_add_report(self):
        name, ok = QInputDialog.getText(self, "New Report", "Report name:")
        name = name.strip()
        if not ok or not name:
            return
        dto = self._report_use_cases.create_report(name)
        index = self._add_tab_for_report(dto.id, dto.name)
        self._tabs.setCurrentIndex(index)

    def _rename_tab(self, index: int):
        if index < 0 or self._is_add_tab(index):
            return
        report_id = self._report_id_for_index(index)
        if report_id is None:
            return
        current_name = self._tabs.tabText(index)
        name, ok = QInputDialog.getText(self, "Rename Report", "Report name:", text=current_name)
        name = name.strip()
        if not ok or not name or name == current_name:
            return
        self._report_use_cases.rename_report(report_id, name)
        self._tabs.setTabText(index, name)

    def _on_tab_context_menu(self, pos):
        index = self._tabs.tabBar().tabAt(pos)
        if index < 0 or self._is_add_tab(index):
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        delete_action.setEnabled(len(self._grids) > 1)
        action = menu.exec(self._tabs.tabBar().mapToGlobal(pos))
        if action == rename_action:
            self._rename_tab(index)
        elif action == delete_action:
            self._delete_tab(index)

    def _delete_tab(self, index: int):
        if len(self._grids) <= 1:
            return
        report_id = self._report_id_for_index(index)
        if report_id is None:
            return
        reply = QMessageBox.question(
            self, "Delete Report",
            f'Delete the report "{self._tabs.tabText(index)}" and all of its widgets?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._report_use_cases.delete_report(report_id)
        grid = self._grids.pop(report_id)
        self._tabs.removeTab(index)
        grid.deleteLater()

    def _on_tab_moved(self, from_index: int, to_index: int):
        add_index = self._tabs.indexOf(self._add_tab_placeholder)
        last_index = self._tabs.count() - 1
        if add_index != -1 and add_index != last_index:
            bar = self._tabs.tabBar()
            bar.blockSignals(True)
            bar.moveTab(add_index, last_index)
            bar.blockSignals(False)

        ordered_ids = [
            self._report_id_for_index(i) for i in range(self._tabs.count())
        ]
        self._report_use_cases.reorder_reports([rid for rid in ordered_ids if rid is not None])
