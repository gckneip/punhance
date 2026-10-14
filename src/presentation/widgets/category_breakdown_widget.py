from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QSizePolicy,
)
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from PySide6.QtGui import QColor
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation.widgets.dashboard.chart_widget import PieChartWidget
from src.presentation.dialogs.category_events_dialog import CategoryEventsDialog
from src.presentation import theme
from src.presentation.i18n import t, format_currency


class CategoryBreakdownWidget(QWidget):
    def __init__(self, category_breakdown_service: CategoryBreakdownService, category_use_cases):
        super().__init__()
        self._breakdown_service = category_breakdown_service
        self._category_use_cases = category_use_cases
        # Filled by refresh(); used to map a clicked pie slice / table row back
        # to the category whose events the modal should list.
        self._categories_map = {}
        self._row_category_ids = []   # parallel to table rows
        self._pie_category_ids = []   # parallel to the (positive-expense) pie slices
        self._range_from = date(2000, 1, 1)
        self._range_to_exclusive = date.today() + timedelta(days=1)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(t("category_breakdown.period")))
        self._date_range = DateRangeSelector(default_label="This Month")
        self._date_range.range_changed.connect(lambda _d: self.refresh())
        filter_row.addWidget(self._date_range)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._income_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("category_breakdown.total_income"), self._income_label))

        self._expenses_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("category_breakdown.total_expenses"), self._expenses_label))

        self._net_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("category_breakdown.net"), self._net_label))

        layout.addLayout(cards_layout)

        # Pie of expenses per category. PieChartWidget defaults to an Ignored
        # size policy (tuned for the fixed-size dashboard grid); here it lives in
        # a free-flowing column, so give it a real vertical footprint.
        self._pie_title = QLabel(t("category_breakdown.pie_title"))
        self._pie_title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-weight: 600;")
        layout.addWidget(self._pie_title)

        self._pie = PieChartWidget()
        self._pie.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pie.setMinimumHeight(240)
        self._pie.slice_clicked.connect(self._on_pie_slice_clicked)
        layout.addWidget(self._pie)

        self._table = EvenColumnsTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            t("common.category"),
            t("category_breakdown.col_income"),
            t("category_breakdown.col_expenses"),
            t("category_breakdown.col_net"),
            t("category_breakdown.col_events"),
        ])
        self._table.setObjectName("mainTabTable")
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.cellClicked.connect(self._on_table_cell_clicked)
        layout.addWidget(self._table)

    def refresh(self):
        date_from, date_to = self._date_range.resolved_range()
        # resolved_range()'s date_to is inclusive; the service's range check is exclusive.
        exclusive_date_to = date_to + timedelta(days=1) if date_to else date.today() + timedelta(days=1)
        self._range_from = date_from or date(2000, 1, 1)
        self._range_to_exclusive = exclusive_date_to
        breakdown = self._breakdown_service.get_breakdown_for_range(
            self._range_from, exclusive_date_to
        )

        self._income_label.setText(format_currency(breakdown.total_income, "BRL"))
        self._expenses_label.setText(format_currency(breakdown.total_expenses, "BRL"))
        net = breakdown.total_income - breakdown.total_expenses
        self._net_label.setText(format_currency(net, "BRL"))
        self._income_label.setStyleSheet(f"color: {theme.INCOME};")
        self._expenses_label.setStyleSheet(f"color: {theme.EXPENSE};")
        self._net_label.setStyleSheet(f"color: {theme.INCOME if net >= 0 else theme.EXPENSE};")

        self._categories_map = {
            c.id: c.name for c in self._category_use_cases.list_categories()
        }

        self._table.setRowCount(len(breakdown.items))
        self._row_category_ids = []
        for i, item in enumerate(breakdown.items):
            self._row_category_ids.append(item.category_id)
            cat_name = self._category_name(item.category_id)
            self._table.setItem(i, 0, QTableWidgetItem(cat_name))
            self._table.setItem(i, 1, QTableWidgetItem(format_currency(item.total_income, "BRL")))
            self._table.setItem(i, 2, QTableWidgetItem(format_currency(item.total_expenses, "BRL")))

            net_item = QTableWidgetItem(format_currency(item.net, "BRL"))
            net_item.setForeground(QColor(theme.INCOME if item.net >= 0 else theme.EXPENSE))
            self._table.setItem(i, 3, net_item)

            self._table.setItem(i, 4, QTableWidgetItem(str(item.event_count)))

        self._table.resizeColumnsToContents()

        # Feed the pie with only the categories that actually spent something,
        # keeping a parallel id list so a clicked slice maps back to its category.
        # (PieChartWidget drops non-positive values, so pre-filtering here keeps
        # slice indices aligned with self._pie_category_ids.)
        self._pie_category_ids = []
        pie_labels, pie_values = [], []
        for item in breakdown.items:
            if item.total_expenses > 0:
                self._pie_category_ids.append(item.category_id)
                pie_labels.append(self._category_name(item.category_id))
                pie_values.append(item.total_expenses)

        if pie_values:
            self._pie.set_series(pie_labels, {"expenses": pie_values})
        else:
            self._pie.set_empty_state(t("chart.no_data"))

    def _category_name(self, category_id):
        return self._categories_map.get(category_id, t("category_breakdown.unassigned"))

    def _on_pie_slice_clicked(self, index, _label):
        if 0 <= index < len(self._pie_category_ids):
            self._open_events_modal(self._pie_category_ids[index])

    def _on_table_cell_clicked(self, row, _col):
        if 0 <= row < len(self._row_category_ids):
            self._open_events_modal(self._row_category_ids[row])

    def _open_events_modal(self, category_id):
        rows = self._breakdown_service.get_events_for_category(
            self._range_from, self._range_to_exclusive, category_id
        )
        dialog = CategoryEventsDialog(self, self._category_name(category_id), rows)
        dialog.exec()
