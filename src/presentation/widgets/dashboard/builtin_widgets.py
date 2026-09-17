from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from src.application.dto.financial_event_dto import CreateFinancialEventDTO
from src.domain.entities.financial_event import EventType
from src.presentation import i18n, icons, theme
from src.presentation.i18n import t
from src.presentation.labels import event_type_label, payment_method_label
from src.presentation.widgets.account_credit_card_selector import AccountCreditCardSelector
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.presentation.widgets.stat_card import make_stat_card

INCOME_TYPES = ("income", "refund")
EXPENSE_TYPES = ("expense", "purchase", "card_payment", "loan_payment", "investment")


def split_event_rows(
    events, accounts=None, categories=None, purchases=None,
    multi_category_event_ids=None, credit_cards=None, installments_by_event=None,
    today: Optional[date] = None,
):
    """Shapes raw events into the row dicts EventsTableWidget renders, split into
    "recent" (due today or earlier) and "future" (due later) buckets - mirrors
    how installment-plan purchases explode into one row per installment."""
    today = today or date.today()
    accounts_map = {a.id: a.name for a in (accounts or [])}
    categories_map = {c.id: c.name for c in (categories or [])}
    cards_map = {c.id: c.name for c in (credit_cards or [])}
    payment_methods_map = {
        p.financial_event_id: payment_method_label(p.payment_method)
        for p in (purchases or [])
    }
    purchase_cards_map = {
        p.financial_event_id: p.credit_card_id for p in (purchases or []) if p.credit_card_id
    }
    multi_category_event_ids = multi_category_event_ids or set()
    installments_by_event = installments_by_event or {}

    recent_rows = []
    future_rows = []
    for e in events:
        cat_name = t("builtin.multiple_categories") if (e.category_id is None and e.id in multi_category_event_ids) \
            else categories_map.get(e.category_id, str(e.category_id or ""))
        if e.account_id:
            acc_name = accounts_map.get(e.account_id, str(e.account_id))
        elif e.id in purchase_cards_map:
            acc_name = cards_map.get(purchase_cards_map[e.id], "")
        else:
            acc_name = ""
        payment_method = payment_methods_map.get(e.id, "")

        event_installments = installments_by_event.get(e.id)
        if event_installments:
            count = len(event_installments)
            for inst in event_installments:
                row = {
                    "date": inst.due_date,
                    "event_type": e.event_type,
                    "description": f"{e.description} ({inst.installment_number}/{count})",
                    "amount": inst.amount,
                    "currency": e.currency,
                    "category": cat_name,
                    "account": acc_name,
                    "payment_method": payment_method,
                    "event_id": e.id,
                }
                (future_rows if inst.due_date > today else recent_rows).append(row)
        else:
            recent_rows.append({
                "date": e.event_date,
                "event_type": e.event_type,
                "description": e.description,
                "amount": e.amount,
                "currency": e.currency,
                "category": cat_name,
                "account": acc_name,
                "payment_method": payment_method,
                "event_id": e.id,
            })

    recent_rows.sort(key=lambda r: r["date"], reverse=True)
    future_rows.sort(key=lambda r: r["date"])
    return recent_rows, future_rows


class QuickAddBarWidget(QFrame):
    entry_added = Signal()

    def __init__(self, financial_event_use_cases, parent=None):
        super().__init__(parent)
        self._financial_event_use_cases = financial_event_use_cases
        self.setObjectName("quickAddBar")
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(6)

        hint = QLabel(t("builtin.quick_add"))
        hint.setStyleSheet(f"font-size: {theme.SMALL_FONT_SIZE}px; font-weight: 600; color: {theme.TEXT_SECONDARY};")
        outer.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._qa_type = QComboBox()
        self._qa_type.addItem(event_type_label(EventType.EXPENSE), EventType.EXPENSE)
        self._qa_type.addItem(event_type_label(EventType.INCOME), EventType.INCOME)
        row.addWidget(self._qa_type)

        self._qa_description = QLineEdit()
        self._qa_description.setPlaceholderText(t("builtin.quick_add_placeholder"))
        self._qa_description.returnPressed.connect(self._quick_add)
        row.addWidget(self._qa_description, stretch=2)

        self._qa_amount = CurrencySpinBox()
        self._qa_amount.setRange(0, 999999)
        self._qa_amount.setDecimals(2)
        self._qa_amount.setPrefix(f'{i18n.CURRENCY_SYMBOLS["BRL"]} ')
        row.addWidget(self._qa_amount)

        self._qa_category = QComboBox()
        row.addWidget(self._qa_category)

        self._qa_selector = AccountCreditCardSelector()
        row.addWidget(self._qa_selector)

        self._qa_button = QPushButton(t("common.add"))
        self._qa_button.setObjectName("primaryButton")
        self._qa_button.clicked.connect(self._quick_add)
        row.addWidget(self._qa_button)

        outer.addLayout(row)

        self._qa_status = QLabel("")
        self._qa_status.setStyleSheet(f"font-size: {theme.SMALL_FONT_SIZE}px;")
        outer.addWidget(self._qa_status)

    def focus(self):
        self._qa_description.setFocus()

    def set_options(self, accounts, categories, credit_cards=None):
        prev_cat = self._qa_category.currentData()

        self._qa_category.blockSignals(True)

        self._qa_category.clear()
        self._qa_category.addItem(t("builtin.no_category"), None)
        for c in categories or []:
            self._qa_category.addItem(c.name, c.id)

        if prev_cat is not None:
            idx = self._qa_category.findData(prev_cat)
            if idx >= 0:
                self._qa_category.setCurrentIndex(idx)

        self._qa_category.blockSignals(False)

        self._qa_selector.set_data(accounts, credit_cards)

    def _quick_add(self):
        description = self._qa_description.text().strip()
        amount = self._qa_amount.value()

        if not description:
            self._show_status(t("builtin.error_description_required"), theme.EXPENSE)
            return
        if amount == 0:
            self._show_status(t("builtin.error_amount_zero"), theme.EXPENSE)
            return
        selector_error = self._qa_selector.validation_error()
        if selector_error:
            self._show_status(selector_error, theme.EXPENSE)
            return

        event_type = self._qa_type.currentData()
        dto = CreateFinancialEventDTO(
            event_type=event_type,
            event_date=date.today(),
            description=description,
            amount=amount,
            category_id=self._qa_category.currentData(),
            account_id=self._qa_selector.account_id(),
            credit_card_id=self._qa_selector.credit_card_id(),
        )
        self._financial_event_use_cases.create_event(dto)

        self._qa_description.clear()
        self._qa_amount.setValue(0)
        self._qa_description.setFocus()
        self._show_status(t("builtin.added"), theme.INCOME, clear_after_ms=2000)
        self.entry_added.emit()

    def _show_status(self, text: str, color: str, clear_after_ms: int = None):
        self._qa_status.setStyleSheet(f"font-size: {theme.SMALL_FONT_SIZE}px; color: {color};")
        self._qa_status.setText(text)
        if clear_after_ms:
            QTimer.singleShot(clear_after_ms, lambda: self._qa_status.setText(""))


class EventsTableWidget(QWidget):
    entry_added = Signal()
    edit_event_requested = Signal(str)

    def __init__(self, mode: str, financial_event_use_cases=None, purchase_use_cases=None, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases
        self._shown_events: List[str] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        self._btn_delete_selected = QPushButton(t("common.delete_selected"))
        self._btn_delete_selected.setIcon(icons.icon("fa6s.trash", color=theme.EXPENSE))
        self._btn_delete_selected.clicked.connect(self._delete_selected)
        toolbar.addWidget(self._btn_delete_selected)
        layout.addLayout(toolbar)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            t("common.date"), t("common.type"), t("common.description"), t("common.amount"),
            t("common.category"), t("builtin.account_card"), t("builtin.payment_method"), t("common.actions"),
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setToolTip(t("builtin.events_table_tooltip"))
        self._table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self._table)

    def set_rows(self, rows: List[dict]):
        rows = rows[:20]
        self._table.setRowCount(0)
        self._table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(i18n.format_date(row["date"])))
            self._table.setItem(i, 1, QTableWidgetItem(event_type_label(row["event_type"])))
            self._table.setItem(i, 2, QTableWidgetItem(row["description"]))

            amount_item = QTableWidgetItem(i18n.format_currency(row["amount"], row["currency"]))
            if row["event_type"] in INCOME_TYPES:
                amount_item.setForeground(QColor(theme.INCOME))
            elif row["event_type"] in EXPENSE_TYPES:
                amount_item.setForeground(QColor(theme.EXPENSE))
            self._table.setItem(i, 3, amount_item)

            self._table.setItem(i, 4, QTableWidgetItem(row["category"]))
            self._table.setItem(i, 5, QTableWidgetItem(row["account"]))
            self._table.setItem(i, 6, QTableWidgetItem(row["payment_method"]))
            self._table.setCellWidget(i, 7, self._make_actions_widget(row["event_id"]))

        self._table.resizeColumnsToContents()
        self._shown_events = [row["event_id"] for row in rows]

    def _make_actions_widget(self, event_id: str) -> QWidget:
        widget = QWidget()
        row_layout = QHBoxLayout(widget)
        row_layout.setContentsMargins(2, 2, 2, 2)
        row_layout.setSpacing(4)
        for label, icon_name, color, handler in [
            (t("common.edit"), "fa6s.pen", None, lambda _: self.edit_event_requested.emit(event_id)),
            (t("common.delete"), "fa6s.trash", theme.EXPENSE, lambda _: self._delete_event(event_id)),
        ]:
            btn = QPushButton()
            btn.setIcon(icons.icon(icon_name, color=color))
            btn.setToolTip(label)
            btn.setFixedWidth(32)
            btn.clicked.connect(handler)
            row_layout.addWidget(btn)
        row_layout.addStretch()
        return widget

    def _on_row_double_clicked(self, row, _column):
        if row < len(self._shown_events):
            self.edit_event_requested.emit(self._shown_events[row])

    def _delete_event_cascade(self, event_id):
        if self._purchase_use_cases is not None:
            self._purchase_use_cases.delete_purchase_by_event(event_id)
        self._financial_event_use_cases.delete_event(event_id)

    def _delete_event(self, event_id):
        if self._financial_event_use_cases is None:
            return
        reply = QMessageBox.question(
            self, t("builtin.delete_event_title"), t("builtin.delete_event_message"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._delete_event_cascade(event_id)
        self.entry_added.emit()

    def _delete_selected(self):
        if self._financial_event_use_cases is None:
            return
        rows = sorted({idx.row() for idx in self._table.selectionModel().selectedRows()})
        event_ids = {self._shown_events[r] for r in rows if r < len(self._shown_events)}
        if not event_ids:
            return
        reply = QMessageBox.question(
            self, t("builtin.delete_events_title"),
            t("builtin.delete_events_message", count=len(event_ids)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for event_id in event_ids:
            self._delete_event_cascade(event_id)
        self.entry_added.emit()


class SavingsRateStatWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._value_label = QLabel("0.0%")
        layout.addWidget(make_stat_card(t("builtin.savings_rate"), self._value_label))

    def set_rate(self, income: float, expenses: float):
        rate = 0.0
        if income > 0:
            rate = ((income - expenses) / income) * 100
        self._value_label.setText(f"{i18n.format_number(rate, 1)}%")
        self._value_label.setStyleSheet(f"color: {theme.INCOME if rate >= 0 else theme.EXPENSE};")
