from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
)
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from PySide6.QtGui import QColor
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation import theme
from src.presentation.i18n import t, format_currency


class CategoryBreakdownWidget(QWidget):
    def __init__(self, category_breakdown_service: CategoryBreakdownService, category_use_cases):
        super().__init__()
        self._breakdown_service = category_breakdown_service
        self._category_use_cases = category_use_cases
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
        layout.addWidget(self._table)

    def refresh(self):
        date_from, date_to = self._date_range.resolved_range()
        # resolved_range()'s date_to is inclusive; the service's range check is exclusive.
        exclusive_date_to = date_to + timedelta(days=1) if date_to else date.today() + timedelta(days=1)
        breakdown = self._breakdown_service.get_breakdown_for_range(
            date_from or date(2000, 1, 1), exclusive_date_to
        )

        self._income_label.setText(format_currency(breakdown.total_income, "BRL"))
        self._expenses_label.setText(format_currency(breakdown.total_expenses, "BRL"))
        net = breakdown.total_income - breakdown.total_expenses
        self._net_label.setText(format_currency(net, "BRL"))
        self._income_label.setStyleSheet(f"color: {theme.INCOME};")
        self._expenses_label.setStyleSheet(f"color: {theme.EXPENSE};")
        self._net_label.setStyleSheet(f"color: {theme.INCOME if net >= 0 else theme.EXPENSE};")

        categories_map = {
            c.id: c.name for c in self._category_use_cases.list_categories()
        }

        self._table.setRowCount(len(breakdown.items))
        for i, item in enumerate(breakdown.items):
            cat_name = categories_map.get(item.category_id, t("category_breakdown.unassigned"))
            self._table.setItem(i, 0, QTableWidgetItem(cat_name))
            self._table.setItem(i, 1, QTableWidgetItem(format_currency(item.total_income, "BRL")))
            self._table.setItem(i, 2, QTableWidgetItem(format_currency(item.total_expenses, "BRL")))

            net_item = QTableWidgetItem(format_currency(item.net, "BRL"))
            net_item.setForeground(QColor(theme.INCOME if item.net >= 0 else theme.EXPENSE))
            self._table.setItem(i, 3, net_item)

            self._table.setItem(i, 4, QTableWidgetItem(str(item.event_count)))

        self._table.resizeColumnsToContents()
