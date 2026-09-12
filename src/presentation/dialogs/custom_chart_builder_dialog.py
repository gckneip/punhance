from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QRadioButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from src.domain.services.chart_data_service import VALID_GROUP_BYS, GroupByDimension, MetricType
from src.presentation.widgets.dashboard.generic_widget_renderer import METRIC_LABELS, build_generic_content
from src.presentation.widgets.dashboard.preview_drawer import PreviewDrawer

CHART_TYPE_LABELS = [("line", "Line"), ("bar", "Bar"), ("pie", "Pie"), ("table", "Table"), ("stat", "Stat")]

GROUP_BY_LABELS = {
    GroupByDimension.NONE: "None (single total)",
    GroupByDimension.MONTH: "Month",
    GroupByDimension.CATEGORY: "Category",
    GroupByDimension.ACCOUNT: "Account",
    GroupByDimension.COUNTERPARTY: "Counterparty",
    GroupByDimension.CREDIT_CARD: "Credit Card",
    GroupByDimension.PRODUCT: "Product",
}


def _multi_select_list(entities) -> QListWidget:
    listbox = QListWidget()
    listbox.setSelectionMode(QListWidget.MultiSelection)
    listbox.setMaximumHeight(90)
    for entity in entities:
        item = QListWidgetItem(entity.name)
        item.setData(Qt.UserRole, entity.id)
        listbox.addItem(item)
    return listbox


def _selected_ids(listbox: QListWidget) -> Optional[List[str]]:
    ids = [item.data(Qt.UserRole) for item in listbox.selectedItems()]
    return ids or None


class CustomChartBuilderDialog(QDialog):
    def __init__(
        self, parent=None, accounts=None, categories=None, counterparties=None,
        credit_cards=None, chart_data_service=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Create Custom Widget")
        self.setModal(True)
        self.resize(820, 620)

        self._accounts = accounts or []
        self._categories = categories or []
        self._counterparties = counterparties or []
        self._credit_cards = credit_cards or []
        self._chart_data_service = chart_data_service

        outer = QVBoxLayout(self)
        content_row = QHBoxLayout()

        form_panel = QWidget()
        layout = QVBoxLayout(form_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_chart_group())
        layout.addWidget(self._build_filters_group())
        layout.addWidget(self._build_date_range_group())
        layout.addStretch()

        content_row.addWidget(form_panel, stretch=1)
        self._preview = PreviewDrawer()
        content_row.addWidget(self._preview)
        outer.addLayout(content_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        # Default to a single checked metric so group-by options (and the preview) populate immediately.
        self._metrics_list.item(0).setCheckState(Qt.Checked)

    def _build_chart_group(self) -> QGroupBox:
        group = QGroupBox("Chart")
        form = QFormLayout(group)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Widget title")
        self._title_edit.textChanged.connect(self._refresh_preview)
        form.addRow("Title:", self._title_edit)

        self._chart_type_combo = QComboBox()
        for value, label in CHART_TYPE_LABELS:
            self._chart_type_combo.addItem(label, value)
        self._chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        form.addRow("Chart type:", self._chart_type_combo)

        self._metrics_list = QListWidget()
        self._metrics_list.setMaximumHeight(120)
        for metric in MetricType:
            item = QListWidgetItem(METRIC_LABELS.get(metric, metric.value))
            item.setData(Qt.UserRole, metric)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._metrics_list.addItem(item)
        self._metrics_list.itemChanged.connect(self._on_metrics_changed)
        form.addRow("Metrics:", self._metrics_list)

        self._group_by_combo = QComboBox()
        self._group_by_combo.currentIndexChanged.connect(self._on_group_by_changed)
        form.addRow("Group by:", self._group_by_combo)

        self._split_by_combo = QComboBox()
        self._split_by_combo.setToolTip(
            "Draw one line/bar per value of this dimension (e.g. one line per "
            "counterparty) across the same month axis. Only available for a single "
            "metric grouped by Month, on a line or bar chart."
        )
        self._split_by_combo.currentIndexChanged.connect(self._on_split_by_changed)
        form.addRow("Split into series by:", self._split_by_combo)

        self._top_n_spin = QSpinBox()
        self._top_n_spin.setRange(2, 20)
        self._top_n_spin.setValue(6)
        self._top_n_spin.setToolTip(
            "Keep the top series by total value; the rest are folded into \"Other\"."
        )
        self._top_n_spin.valueChanged.connect(self._refresh_preview)
        form.addRow("Show top:", self._top_n_spin)

        return group

    def _build_filters_group(self) -> QGroupBox:
        group = QGroupBox("Filters (optional)")
        form = QFormLayout(group)
        hint = QLabel("Leave a list empty to not restrict by it.")
        hint.setWordWrap(True)
        form.addRow(hint)

        self._account_filter = _multi_select_list(self._accounts)
        self._account_filter.itemSelectionChanged.connect(self._refresh_preview)
        form.addRow("Accounts:", self._account_filter)
        self._category_filter = _multi_select_list(self._categories)
        self._category_filter.itemSelectionChanged.connect(self._refresh_preview)
        form.addRow("Categories:", self._category_filter)
        self._counterparty_filter = _multi_select_list(self._counterparties)
        self._counterparty_filter.itemSelectionChanged.connect(self._refresh_preview)
        form.addRow("Counterparties:", self._counterparty_filter)
        self._credit_card_filter = _multi_select_list(self._credit_cards)
        self._credit_card_filter.itemSelectionChanged.connect(self._refresh_preview)
        form.addRow("Credit cards:", self._credit_card_filter)
        return group

    def _build_date_range_group(self) -> QGroupBox:
        group = QGroupBox("Date range")
        outer = QVBoxLayout(group)

        radios = QHBoxLayout()
        self._mode_group = QButtonGroup(self)
        self._fixed_radio = QRadioButton("Fixed")
        self._rolling_radio = QRadioButton("Rolling")
        self._calendar_radio = QRadioButton("Calendar")
        self._rolling_radio.setChecked(True)
        for i, radio in enumerate([self._fixed_radio, self._rolling_radio, self._calendar_radio]):
            self._mode_group.addButton(radio, i)
            radios.addWidget(radio)
        outer.addLayout(radios)

        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(self._build_fixed_panel())
        self._mode_stack.addWidget(self._build_rolling_panel())
        self._mode_stack.addWidget(self._build_calendar_panel())
        outer.addWidget(self._mode_stack)

        self._mode_group.idClicked.connect(self._mode_stack.setCurrentIndex)
        self._mode_group.idClicked.connect(self._refresh_preview)
        self._mode_stack.setCurrentIndex(1)
        return group

    def _build_fixed_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        self._fixed_from = QDateEdit()
        self._fixed_from.setCalendarPopup(True)
        self._fixed_from.dateChanged.connect(self._refresh_preview)
        self._fixed_to = QDateEdit()
        self._fixed_to.setCalendarPopup(True)
        self._fixed_to.dateChanged.connect(self._refresh_preview)
        form.addRow("From:", self._fixed_from)
        form.addRow("To:", self._fixed_to)
        return panel

    def _build_rolling_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        self._rolling_amount = QSpinBox()
        self._rolling_amount.setRange(1, 60)
        self._rolling_amount.setValue(6)
        self._rolling_amount.valueChanged.connect(self._refresh_preview)
        self._rolling_unit = QComboBox()
        self._rolling_unit.addItem("Months", "months")
        self._rolling_unit.addItem("Days", "days")
        self._rolling_unit.currentIndexChanged.connect(self._refresh_preview)
        form.addRow("Last:", self._rolling_amount)
        form.addRow("Unit:", self._rolling_unit)
        return panel

    def _build_calendar_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        self._calendar_period = QComboBox()
        self._calendar_period.addItem("Month", "month")
        self._calendar_period.addItem("Year", "year")
        self._calendar_period.currentIndexChanged.connect(self._refresh_preview)
        self._calendar_offset = QSpinBox()
        self._calendar_offset.setRange(-24, 0)
        self._calendar_offset.setValue(0)
        self._calendar_offset.setToolTip("0 = current period, -1 = previous period, ...")
        self._calendar_offset.valueChanged.connect(self._refresh_preview)
        form.addRow("Period:", self._calendar_period)
        form.addRow("Offset:", self._calendar_offset)
        return panel

    def _selected_metrics(self) -> List[MetricType]:
        metrics = []
        for i in range(self._metrics_list.count()):
            item = self._metrics_list.item(i)
            if item.checkState() == Qt.Checked:
                metrics.append(item.data(Qt.UserRole))
        return metrics

    def _chart_type(self) -> str:
        return self._chart_type_combo.currentData()

    def _on_chart_type_changed(self):
        chart_type = self._chart_type()
        if chart_type == "stat":
            # Stat shows a single number: force exactly one checked metric.
            checked = self._selected_metrics()
            if len(checked) != 1:
                self._metrics_list.blockSignals(True)
                for i in range(self._metrics_list.count()):
                    item = self._metrics_list.item(i)
                    item.setCheckState(Qt.Checked if i == 0 else Qt.Unchecked)
                self._metrics_list.blockSignals(False)
        self._refresh_group_by_options()
        self._refresh_split_by_options()
        self._refresh_preview()

    def _on_metrics_changed(self, changed_item: QListWidgetItem):
        if self._chart_type() == "stat" and changed_item.checkState() == Qt.Checked:
            self._metrics_list.blockSignals(True)
            for i in range(self._metrics_list.count()):
                item = self._metrics_list.item(i)
                if item is not changed_item:
                    item.setCheckState(Qt.Unchecked)
            self._metrics_list.blockSignals(False)
        self._refresh_group_by_options()
        self._refresh_split_by_options()
        self._refresh_preview()

    def _on_group_by_changed(self, *_args):
        self._refresh_split_by_options()
        self._refresh_preview()

    def _on_split_by_changed(self, *_args):
        self._top_n_spin.setEnabled(
            self._split_by_combo.isEnabled() and self._split_by_combo.currentData() is not None
        )
        self._refresh_preview()

    def _split_by_allowed_dims(self) -> set:
        metrics = self._selected_metrics()
        if self._chart_type() not in ("line", "bar") or len(metrics) != 1:
            return set()
        if self._group_by_combo.currentData() != GroupByDimension.MONTH:
            return set()
        return set(VALID_GROUP_BYS.get(metrics[0], ())) - {GroupByDimension.NONE, GroupByDimension.MONTH}

    def _refresh_split_by_options(self):
        allowed = self._split_by_allowed_dims()
        prev = self._split_by_combo.currentData()

        self._split_by_combo.blockSignals(True)
        self._split_by_combo.clear()
        self._split_by_combo.addItem("Don't split", None)
        for dim in GroupByDimension:
            if dim in allowed:
                self._split_by_combo.addItem(GROUP_BY_LABELS.get(dim, dim.value), dim)
        if prev is not None:
            idx = self._split_by_combo.findData(prev)
            if idx >= 0:
                self._split_by_combo.setCurrentIndex(idx)
        self._split_by_combo.blockSignals(False)

        self._split_by_combo.setEnabled(bool(allowed))
        self._top_n_spin.setEnabled(
            self._split_by_combo.isEnabled() and self._split_by_combo.currentData() is not None
        )

    def _refresh_group_by_options(self):
        metrics = self._selected_metrics()
        chart_type = self._chart_type()
        prev = self._group_by_combo.currentData()

        if metrics:
            allowed = set(VALID_GROUP_BYS.get(metrics[0], ()))
            for metric in metrics[1:]:
                allowed &= set(VALID_GROUP_BYS.get(metric, ()))
        else:
            allowed = set()

        if chart_type == "stat":
            allowed &= {GroupByDimension.NONE}
        elif chart_type == "pie":
            allowed -= {GroupByDimension.NONE, GroupByDimension.MONTH}

        self._group_by_combo.blockSignals(True)
        self._group_by_combo.clear()
        for dim in GroupByDimension:
            if dim in allowed:
                self._group_by_combo.addItem(GROUP_BY_LABELS.get(dim, dim.value), dim)
        if prev is not None:
            idx = self._group_by_combo.findData(prev)
            if idx >= 0:
                self._group_by_combo.setCurrentIndex(idx)
        self._group_by_combo.blockSignals(False)

    def _refresh_preview(self, *_args):
        title = self._title_edit.text().strip() or "Preview"

        if self._chart_data_service is None:
            self._preview.set_title(title)
            self._preview.show_placeholder("Preview unavailable.")
            return
        if not self._selected_metrics():
            self._preview.set_title(title)
            self._preview.show_placeholder("Select at least one metric to preview this widget.")
            return
        if self._group_by_combo.currentData() is None:
            self._preview.set_title(title)
            self._preview.show_placeholder("Select a valid \"Group by\" option to preview this widget.")
            return

        self._preview.set_title(title)
        config = self._build_config()
        try:
            content = build_generic_content(title, config, self._chart_data_service)
        except Exception:
            self._preview.show_placeholder("Couldn't render a preview for this configuration.")
            return
        self._preview.show_content(content, center=(config["chart_type"] == "stat"))

    def _validate_and_accept(self):
        if not self._title_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        if not self._selected_metrics():
            QMessageBox.warning(self, "Validation", "Select at least one metric.")
            return
        if self._group_by_combo.count() == 0:
            QMessageBox.warning(self, "Validation", "No valid grouping for the selected metrics/chart type.")
            return
        self.accept()

    def _current_date_range_dict(self) -> dict:
        if self._fixed_radio.isChecked():
            return {
                "mode": "fixed",
                "date_from": self._fixed_from.date().toPython().isoformat(),
                "date_to": self._fixed_to.date().toPython().isoformat(),
            }
        if self._calendar_radio.isChecked():
            return {
                "mode": "calendar",
                "period": self._calendar_period.currentData(),
                "offset": self._calendar_offset.value(),
            }
        return {
            "mode": "rolling",
            "unit": self._rolling_unit.currentData(),
            "amount": self._rolling_amount.value(),
        }

    def _current_filters_dict(self) -> dict:
        filters = {
            "account_ids": _selected_ids(self._account_filter),
            "category_ids": _selected_ids(self._category_filter),
            "counterparty_ids": _selected_ids(self._counterparty_filter),
            "credit_card_ids": _selected_ids(self._credit_card_filter),
        }
        return {k: v for k, v in filters.items() if v}

    def _build_config(self) -> dict:
        group_by_data = self._group_by_combo.currentData()
        group_by = group_by_data.value if group_by_data is not None else GroupByDimension.NONE.value
        config = {
            "chart_type": self._chart_type(),
            "metrics": [m.value for m in self._selected_metrics()],
            "group_by": group_by,
            "date_range": self._current_date_range_dict(),
            "filters": self._current_filters_dict(),
        }
        split_by_data = self._split_by_combo.currentData() if self._split_by_combo.isEnabled() else None
        if split_by_data is not None:
            config["split_by"] = split_by_data.value
            config["top_n"] = self._top_n_spin.value()
        return config

    def get_data(self) -> dict:
        return {"title": self._title_edit.text().strip(), "config": self._build_config()}
