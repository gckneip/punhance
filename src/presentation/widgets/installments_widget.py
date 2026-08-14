from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QMessageBox,
)
from PySide6.QtGui import QColor
from src.application.dto.installment_dto import InstallmentDTO
from src.application.dto.credit_card_dto import CreditCardDTO
from src.presentation import theme


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
        filter_row.addWidget(QLabel("Card:"))
        filter_row.addWidget(self._card_combo)

        self._status_combo = QComboBox()
        self._status_combo.addItems(["All", "pending", "paid", "overdue", "cancelled"])
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self._status_combo)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self.refresh)
        filter_row.addWidget(self._btn_refresh)

        self._btn_mark_paid = QPushButton("Mark Selected as Paid")
        self._btn_mark_paid.clicked.connect(self._mark_selected_paid)
        filter_row.addWidget(self._btn_mark_paid)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Due Date", "Installment", "Amount", "Status", "Plan ID", "ID"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def update_cards(self, credit_cards: List[CreditCardDTO]):
        self._card_combo.clear()
        self._card_combo.addItem("All Cards", None)
        for cc in credit_cards:
            self._card_combo.addItem(f"{cc.name} ({cc.issuer})", cc.id)

    def refresh(self, credit_cards: Optional[List[CreditCardDTO]] = None):
        if credit_cards is not None:
            self.update_cards(credit_cards)

        status_text = self._status_combo.currentText()
        status = status_text if status_text != "All" else None
        card_id = self._card_combo.currentData()

        installments = self._installment_use_cases.list_installments(
            status=status,
            credit_card_id=card_id,
        )
        self._installments = installments

        self._table.setRowCount(len(installments))
        for i, inst in enumerate(installments):
            self._table.setItem(i, 0, QTableWidgetItem(inst.due_date.isoformat()))
            self._table.setItem(i, 1, QTableWidgetItem(f"{inst.installment_number}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"R$ {inst.amount:.2f}"))

            status_item = QTableWidgetItem(inst.status)
            if inst.status == "overdue":
                status_item.setForeground(QColor(theme.EXPENSE))
            elif inst.status == "paid":
                status_item.setForeground(QColor(theme.INCOME))
            self._table.setItem(i, 3, status_item)
            self._table.setItem(i, 4, QTableWidgetItem(inst.installment_plan_id))
            self._table.setItem(i, 5, QTableWidgetItem(inst.id))

        self._table.resizeColumnsToContents()

    def _mark_selected_paid(self):
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "Info", "Select an installment to mark as paid.")
            return
        for row in rows:
            if row < len(self._installments):
                self._installment_use_cases.mark_as_paid(self._installments[row].id)
        self.refresh()
