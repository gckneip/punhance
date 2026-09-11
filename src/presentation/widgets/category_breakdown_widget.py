from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QDateEdit, QPushButton,
)
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation import theme


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

        self._month_date = QDateEdit()
        self._month_date.setCalendarPopup(True)
        today = date.today()
        self._month_date.setDate(QDate(today.year, today.month, 1))
        self._month_date.setDisplayFormat("yyyy-MM")
        filter_row.addWidget(QLabel("Month:"))
        filter_row.addWidget(self._month_date)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self.refresh)
        filter_row.addWidget(self._btn_refresh)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._income_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Total Income", self._income_label))

        self._expenses_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Total Expenses", self._expenses_label))

        self._net_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Net", self._net_label))

        layout.addLayout(cards_layout)

        self._table = EvenColumnsTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Category", "Income", "Expenses", "Net", "Events"]
        )
        self._table.setObjectName("mainTabTable")
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def refresh(self):
        qdate = self._month_date.date()
        year = qdate.year()
        month = qdate.month()

        breakdown = self._breakdown_service.get_breakdown(year, month)

        self._income_label.setText(f"R$ {breakdown.total_income:.2f}")
        self._expenses_label.setText(f"R$ {breakdown.total_expenses:.2f}")
        net = breakdown.total_income - breakdown.total_expenses
        self._net_label.setText(f"R$ {net:.2f}")
        self._income_label.setStyleSheet(f"color: {theme.INCOME};")
        self._expenses_label.setStyleSheet(f"color: {theme.EXPENSE};")
        self._net_label.setStyleSheet(f"color: {theme.INCOME if net >= 0 else theme.EXPENSE};")

        categories_map = {
            c.id: c.name for c in self._category_use_cases.list_categories()
        }

        self._table.setRowCount(len(breakdown.items))
        for i, item in enumerate(breakdown.items):
            cat_name = categories_map.get(item.category_id, "Unassigned")
            self._table.setItem(i, 0, QTableWidgetItem(cat_name))
            self._table.setItem(i, 1, QTableWidgetItem(f"R$ {item.total_income:.2f}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"R$ {item.total_expenses:.2f}"))

            net_item = QTableWidgetItem(f"R$ {item.net:.2f}")
            net_item.setForeground(QColor(theme.INCOME if item.net >= 0 else theme.EXPENSE))
            self._table.setItem(i, 3, net_item)

            self._table.setItem(i, 4, QTableWidgetItem(str(item.event_count)))

        self._table.resizeColumnsToContents()
