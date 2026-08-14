from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QFrame, QComboBox, QLineEdit, QDoubleSpinBox, QPushButton,
)
from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QColor
from src.domain.services.monthly_summary_service import MonthlySummaryService
from src.domain.entities.financial_event import EventType
from src.application.dto.financial_event_dto import CreateFinancialEventDTO
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation import theme

INCOME_TYPES = ("income", "refund")
EXPENSE_TYPES = ("expense", "purchase", "card_payment", "loan_payment", "investment")


class DashboardWidget(QWidget):
    entry_added = Signal()

    def __init__(self, monthly_summary_service: MonthlySummaryService, financial_event_use_cases=None):
        super().__init__()
        self._summary_service = monthly_summary_service
        self._financial_event_use_cases = financial_event_use_cases
        self._accounts = []
        self._categories = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        today = date.today()
        summary = self._summary_service.get_summary(today.year, today.month)

        layout.addWidget(self._build_quick_add_bar())

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._balance_label = QLabel("R$ 0.00")
        cards_layout.addWidget(make_stat_card("Monthly Net", self._balance_label))

        self._income_label = QLabel(f"R$ {summary.income:.2f}")
        cards_layout.addWidget(make_stat_card("Monthly Income", self._income_label))

        self._expenses_label = QLabel(f"R$ {summary.expenses:.2f}")
        cards_layout.addWidget(make_stat_card("Monthly Expenses", self._expenses_label))

        savings_rate = 0
        if summary.income > 0:
            savings_rate = ((summary.income - summary.expenses) / summary.income) * 100
        self._savings_label = QLabel(f"{savings_rate:.1f}%")
        cards_layout.addWidget(make_stat_card("Savings Rate", self._savings_label))

        layout.addLayout(cards_layout)
        self._apply_summary_colors(summary.income, summary.expenses, summary.net)

        title = QLabel("Recent Events")
        title.setStyleSheet("font-size: 14px; font-weight: 600; margin-top: 6px;")
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["Date", "Type", "Description", "Amount", "Category", "Account"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def _build_quick_add_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("quickAddBar")

        outer = QVBoxLayout(bar)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(6)

        hint = QLabel("Quick add")
        hint.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {theme.TEXT_SECONDARY};")
        outer.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._qa_type = QComboBox()
        self._qa_type.addItems(["Expense", "Income"])
        row.addWidget(self._qa_type)

        self._qa_description = QLineEdit()
        self._qa_description.setPlaceholderText("What was it?")
        self._qa_description.returnPressed.connect(self._quick_add)
        row.addWidget(self._qa_description, stretch=2)

        self._qa_amount = QDoubleSpinBox()
        self._qa_amount.setRange(0, 999999)
        self._qa_amount.setDecimals(2)
        self._qa_amount.setPrefix("R$ ")
        row.addWidget(self._qa_amount)

        self._qa_category = QComboBox()
        row.addWidget(self._qa_category)

        self._qa_account = QComboBox()
        row.addWidget(self._qa_account)

        self._qa_button = QPushButton("Add")
        self._qa_button.setObjectName("primaryButton")
        self._qa_button.clicked.connect(self._quick_add)
        row.addWidget(self._qa_button)

        outer.addLayout(row)

        self._qa_status = QLabel("")
        self._qa_status.setStyleSheet("font-size: 11px;")
        outer.addWidget(self._qa_status)

        return bar

    def focus_quick_add(self):
        self._qa_description.setFocus()

    def _populate_quick_add_combos(self):
        prev_cat = self._qa_category.currentData()
        prev_acc = self._qa_account.currentData()

        self._qa_category.blockSignals(True)
        self._qa_account.blockSignals(True)

        self._qa_category.clear()
        self._qa_category.addItem("No category", None)
        for c in self._categories:
            self._qa_category.addItem(c.name, c.id)

        self._qa_account.clear()
        self._qa_account.addItem("No account", None)
        for a in self._accounts:
            self._qa_account.addItem(a.name, a.id)

        if prev_cat is not None:
            idx = self._qa_category.findData(prev_cat)
            if idx >= 0:
                self._qa_category.setCurrentIndex(idx)
        if prev_acc is not None:
            idx = self._qa_account.findData(prev_acc)
            if idx >= 0:
                self._qa_account.setCurrentIndex(idx)

        self._qa_category.blockSignals(False)
        self._qa_account.blockSignals(False)

    def _quick_add(self):
        if self._financial_event_use_cases is None:
            return

        description = self._qa_description.text().strip()
        amount = self._qa_amount.value()

        if not description:
            self._show_qa_status("Description is required.", theme.EXPENSE)
            return
        if amount == 0:
            self._show_qa_status("Amount cannot be zero.", theme.EXPENSE)
            return

        event_type = EventType.INCOME if self._qa_type.currentText() == "Income" else EventType.EXPENSE
        dto = CreateFinancialEventDTO(
            event_type=event_type,
            event_date=date.today(),
            description=description,
            amount=amount,
            category_id=self._qa_category.currentData(),
            account_id=self._qa_account.currentData(),
        )
        self._financial_event_use_cases.create_event(dto)

        self._qa_description.clear()
        self._qa_amount.setValue(0)
        self._qa_description.setFocus()
        self._show_qa_status("Added", theme.INCOME, clear_after_ms=2000)
        self.entry_added.emit()

    def _show_qa_status(self, text: str, color: str, clear_after_ms: int = None):
        self._qa_status.setStyleSheet(f"font-size: 11px; color: {color};")
        self._qa_status.setText(text)
        if clear_after_ms:
            QTimer.singleShot(clear_after_ms, lambda: self._qa_status.setText(""))

    def _apply_summary_colors(self, income: float, expenses: float, net: float):
        self._income_label.setStyleSheet(f"color: {theme.INCOME};")
        self._expenses_label.setStyleSheet(f"color: {theme.EXPENSE};")
        self._balance_label.setStyleSheet(f"color: {theme.INCOME if net >= 0 else theme.EXPENSE};")

    def refresh(self, events, accounts=None, categories=None, counterparties=None):
        self._accounts = accounts or []
        self._categories = categories or []
        self._populate_quick_add_combos()

        today = date.today()
        summary = self._summary_service.get_summary(today.year, today.month)

        self._balance_label.setText(f"R$ {summary.net:.2f}")
        self._income_label.setText(f"R$ {summary.income:.2f}")
        self._expenses_label.setText(f"R$ {summary.expenses:.2f}")
        self._apply_summary_colors(summary.income, summary.expenses, summary.net)

        savings_rate = 0
        if summary.income > 0:
            savings_rate = ((summary.income - summary.expenses) / summary.income) * 100
        self._savings_label.setText(f"{savings_rate:.1f}%")

        accounts_map = {a.id: a.name for a in self._accounts}
        categories_map = {c.id: c.name for c in self._categories}

        shown_events = events[:20]
        self._table.setRowCount(len(shown_events))
        for i, e in enumerate(shown_events):
            self._table.setItem(i, 0, QTableWidgetItem(e.event_date.isoformat()))
            self._table.setItem(i, 1, QTableWidgetItem(e.event_type))
            self._table.setItem(i, 2, QTableWidgetItem(e.description))

            amount_item = QTableWidgetItem(f"{e.currency} {e.amount:.2f}")
            if e.event_type in INCOME_TYPES:
                amount_item.setForeground(QColor(theme.INCOME))
            elif e.event_type in EXPENSE_TYPES:
                amount_item.setForeground(QColor(theme.EXPENSE))
            self._table.setItem(i, 3, amount_item)

            cat_name = categories_map.get(e.category_id, str(e.category_id or ""))
            acc_name = accounts_map.get(e.account_id, str(e.account_id or ""))
            self._table.setItem(i, 4, QTableWidgetItem(cat_name))
            self._table.setItem(i, 5, QTableWidgetItem(acc_name))

        self._table.resizeColumnsToContents()
