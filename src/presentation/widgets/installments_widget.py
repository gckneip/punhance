from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel,
)
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from PySide6.QtGui import QColor
from src.application.dto.installment_dto import InstallmentDTO
from src.application.dto.credit_card_dto import CreditCardDTO
from src.presentation import theme
from src.presentation.i18n import t, format_currency, format_date
from src.presentation.labels import installment_status_label


class InstallmentsWidget(QWidget):
    def __init__(self, installment_use_cases):
        super().__init__()
        self._installment_use_cases = installment_use_cases
        self._installments: List[InstallmentDTO] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        filter_row = QHBoxLayout()

        self._card_combo = QComboBox()
        filter_row.addWidget(QLabel(t("installments.card_filter")))
        filter_row.addWidget(self._card_combo)

        self._status_combo = QComboBox()
        self._status_combo.addItem(t("installments.status_all"), None)
        self._status_combo.addItem(installment_status_label("pending"), "pending")
        self._status_combo.addItem(installment_status_label("overdue"), "overdue")
        filter_row.addWidget(QLabel(t("installments.status_filter")))
        filter_row.addWidget(self._status_combo)

        self._btn_refresh = QPushButton(t("installments.refresh"))
        self._btn_refresh.clicked.connect(self.refresh)
        filter_row.addWidget(self._btn_refresh)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        self._table = EvenColumnsTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            t("installments.col_due_date"),
            t("installments.col_installment"),
            t("common.amount"),
            t("common.status"),
            t("installments.col_plan_id"),
            t("installments.col_id"),
        ])
        self._table.setObjectName("mainTabTable")
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def update_cards(self, credit_cards: List[CreditCardDTO]):
        self._card_combo.clear()
        self._card_combo.addItem(t("installments.all_cards"), None)
        for cc in credit_cards:
            self._card_combo.addItem(f"{cc.name} ({cc.issuer})", cc.id)

    def refresh(self, credit_cards: Optional[List[CreditCardDTO]] = None):
        if credit_cards is not None:
            self.update_cards(credit_cards)

        status = self._status_combo.currentData()
        card_id = self._card_combo.currentData()

        installments = self._installment_use_cases.list_installments(
            status=status,
            credit_card_id=card_id,
        )
        self._installments = installments

        self._table.setRowCount(len(installments))
        for i, inst in enumerate(installments):
            self._table.setItem(i, 0, QTableWidgetItem(format_date(inst.due_date)))
            self._table.setItem(i, 1, QTableWidgetItem(f"{inst.installment_number}"))
            self._table.setItem(i, 2, QTableWidgetItem(format_currency(inst.amount, "BRL")))

            status_item = QTableWidgetItem(installment_status_label(inst.status))
            if inst.status == "overdue":
                status_item.setForeground(QColor(theme.EXPENSE))
            elif inst.status == "paid":
                status_item.setForeground(QColor(theme.INCOME))
            self._table.setItem(i, 3, status_item)
            self._table.setItem(i, 4, QTableWidgetItem(inst.installment_plan_id))
            self._table.setItem(i, 5, QTableWidgetItem(inst.id))

        self._table.resizeColumnsToContents()
