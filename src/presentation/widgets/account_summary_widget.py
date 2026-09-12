from datetime import timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
)
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from PySide6.QtGui import QColor
from src.domain.services.account_summary_service import AccountSummaryService
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation import theme


class AccountSummaryWidget(QWidget):
    def __init__(self, account_summary_service: AccountSummaryService):
        super().__init__()
        self._summary_service = account_summary_service
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Period:"))
        self._date_range = DateRangeSelector(default_label="All Time")
        self._date_range.range_changed.connect(lambda _d: self.refresh())
        filter_row.addWidget(self._date_range)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._total_balance_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Total Balance", self._total_balance_label))

        self._total_income_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Total Income", self._total_income_label))

        self._total_expenses_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Total Expenses", self._total_expenses_label))

        layout.addLayout(cards_layout)

        self._table = EvenColumnsTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Account", "Type", "Initial Balance", "Income", "Expenses", "Current Balance"]
        )
        self._table.setObjectName("mainTabTable")
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def refresh(self):
        date_from, date_to = self._date_range.resolved_range()

        # The repository treats date_to as an exclusive upper bound, but
        # resolved_range()'s date_to is inclusive of that whole day.
        summary = self._summary_service.get_summary(
            date_from=date_from, date_to=date_to + timedelta(days=1) if date_to else None
        )

        self._total_balance_label.setText(f"R$ {summary.grand_total:.2f}")
        self._total_income_label.setText(f"R$ {summary.total_income:.2f}")
        self._total_expenses_label.setText(f"R$ {summary.total_expenses:.2f}")
        self._total_income_label.setStyleSheet(f"color: {theme.INCOME};")
        self._total_expenses_label.setStyleSheet(f"color: {theme.EXPENSE};")
        self._total_balance_label.setStyleSheet(
            f"color: {theme.INCOME if summary.grand_total >= 0 else theme.EXPENSE};"
        )

        self._table.setRowCount(len(summary.items))
        for i, item in enumerate(summary.items):
            self._table.setItem(i, 0, QTableWidgetItem(item.account_name))
            self._table.setItem(i, 1, QTableWidgetItem(item.account_type))
            self._table.setItem(i, 2, QTableWidgetItem(f"R$ {item.initial_balance:.2f}"))
            self._table.setItem(i, 3, QTableWidgetItem(f"R$ {item.total_income:.2f}"))
            self._table.setItem(i, 4, QTableWidgetItem(f"R$ {item.total_expenses:.2f}"))

            balance_item = QTableWidgetItem(f"R$ {item.current_balance:.2f}")
            balance_item.setForeground(
                QColor(theme.INCOME if item.current_balance >= 0 else theme.EXPENSE)
            )
            self._table.setItem(i, 5, balance_item)

        self._table.resizeColumnsToContents()
