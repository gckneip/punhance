from typing import Callable, List
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDateEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
    QCheckBox, QSpinBox, QDialogButtonBox, QWidget,
)
from PySide6.QtCore import QDate
from src.application.dto.category_dto import CategoryDTO
from src.application.dto.credit_card_dto import CreditCardDTO
from src.application.dto.counterparty_dto import CounterpartyDTO
from src.presentation.dialogs.counterparty_dialog import CounterpartyDialog


class PurchaseDialog(QDialog):
    def __init__(
        self,
        categories: List[CategoryDTO],
        credit_cards: List[CreditCardDTO],
        counterparties: List[CounterpartyDTO],
        on_create_counterparty: Callable[[str], CounterpartyDTO],
        parent=None,
    ):
        super().__init__(parent)
        self._categories = categories
        self._credit_cards = credit_cards
        self._counterparties = counterparties
        self._on_create_counterparty = on_create_counterparty

        self.setWindowTitle("Create Purchase")
        self.setModal(True)
        self.resize(600, 550)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date:", self.date_edit)

        self.description_edit = QLineEdit()
        form.addRow("Description:", self.description_edit)

        self.total_spin = QDoubleSpinBox()
        self.total_spin.setRange(0.01, 999999)
        self.total_spin.setPrefix("R$ ")
        form.addRow("Total Amount:", self.total_spin)

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["credit_card", "debit_card", "cash", "pix", "bank_transfer"])
        self.payment_combo.currentTextChanged.connect(self._on_payment_changed)
        form.addRow("Payment Method:", self.payment_combo)

        self.card_combo = QComboBox()
        self.card_combo.addItem("None", None)
        for cc in credit_cards:
            self.card_combo.addItem(f"{cc.name} ({cc.issuer})", cc.id)
        form.addRow("Credit Card:", self.card_combo)

        self.installments_check = QCheckBox("Has installments")
        self.installments_check.toggled.connect(self._on_installments_toggled)
        form.addRow(self.installments_check)

        self.installments_spin = QSpinBox()
        self.installments_spin.setRange(2, 120)
        self.installments_spin.setValue(2)
        self.installments_spin.setEnabled(False)
        form.addRow("Installment Count:", self.installments_spin)

        self.counterparty_combo = QComboBox()
        self.counterparty_combo.addItem("None", None)
        for cp in counterparties:
            self.counterparty_combo.addItem(cp.name, cp.id)

        counterparty_row = QWidget()
        counterparty_row_layout = QHBoxLayout(counterparty_row)
        counterparty_row_layout.setContentsMargins(0, 0, 0, 0)
        counterparty_row_layout.addWidget(self.counterparty_combo)
        self._btn_add_counterparty = QPushButton("+")
        self._btn_add_counterparty.setFixedWidth(28)
        self._btn_add_counterparty.setToolTip("New counterparty")
        self._btn_add_counterparty.clicked.connect(self._add_counterparty)
        counterparty_row_layout.addWidget(self._btn_add_counterparty)
        form.addRow("Counterparty:", counterparty_row)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        items_label = QLabel("Items (optional):")
        items_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(items_label)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["Name", "Qty", "Unit", "Unit Price", "Total", "Category"]
        )
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setAlternatingRowColors(True)
        layout.addWidget(self.items_table)

        btn_row = QHBoxLayout()
        self._btn_add_item = QPushButton("+ Add Item")
        self._btn_add_item.clicked.connect(self._add_item_row)
        btn_row.addWidget(self._btn_add_item)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_payment_changed(self, method: str):
        self.card_combo.setEnabled(method == "credit_card")

    def _on_installments_toggled(self, checked: bool):
        self.installments_spin.setEnabled(checked)

    def _add_counterparty(self):
        dialog = CounterpartyDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            new_cp = self._on_create_counterparty(data["name"])
            self.counterparty_combo.addItem(new_cp.name, new_cp.id)
            self.counterparty_combo.setCurrentIndex(self.counterparty_combo.count() - 1)

    def _add_item_row(self, name="", qty=1.0, unit="UNIT", unit_price=0.0, total=0.0, cat_id=None):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        name_item = QTableWidgetItem(name)
        self.items_table.setItem(row, 0, name_item)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.01, 999999)
        qty_spin.setDecimals(3)
        qty_spin.setValue(qty)
        self.items_table.setCellWidget(row, 1, qty_spin)

        unit_combo = QComboBox()
        unit_combo.addItems(["UNIT", "KG", "G", "L", "ML", "BOX", "PACK"])
        unit_combo.setCurrentText(unit)
        self.items_table.setCellWidget(row, 2, unit_combo)

        price_spin = QDoubleSpinBox()
        price_spin.setRange(0, 999999)
        price_spin.setDecimals(2)
        price_spin.setPrefix("R$ ")
        price_spin.setValue(unit_price)
        self.items_table.setCellWidget(row, 3, price_spin)

        total_spin = QDoubleSpinBox()
        total_spin.setRange(0, 999999)
        total_spin.setDecimals(2)
        total_spin.setPrefix("R$ ")
        total_spin.setValue(total)
        self.items_table.setCellWidget(row, 4, total_spin)

        cat_combo = QComboBox()
        cat_combo.addItem("None", None)
        for c in self._categories:
            cat_combo.addItem(c.name, c.id)
        if cat_id:
            idx = cat_combo.findData(cat_id)
            if idx >= 0:
                cat_combo.setCurrentIndex(idx)
        self.items_table.setCellWidget(row, 5, cat_combo)

        self.items_table.resizeColumnsToContents()

    def _validate_and_accept(self):
        if not self.description_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Description is required.")
            return
        self.accept()

    def get_data(self):
        items = []
        for row in range(self.items_table.rowCount()):
            name = self.items_table.item(row, 0).text().strip() if self.items_table.item(row, 0) else ""
            qty = self.items_table.cellWidget(row, 1).value()
            unit = self.items_table.cellWidget(row, 2).currentText()
            unit_price = self.items_table.cellWidget(row, 3).value()
            total = self.items_table.cellWidget(row, 4).value()
            cat_id = self.items_table.cellWidget(row, 5).currentData()
            items.append({
                "name": name,
                "quantity": qty,
                "unit": unit,
                "unit_price": unit_price,
                "total_price": total,
                "category_id": cat_id,
            })

        return {
            "event_date": self.date_edit.date().toPython(),
            "description": self.description_edit.text().strip(),
            "total_amount": self.total_spin.value(),
            "payment_method": self.payment_combo.currentText(),
            "credit_card_id": self.card_combo.currentData(),
            "notes": self.notes_edit.toPlainText().strip() or None,
            "installment_count": self.installments_spin.value() if self.installments_check.isChecked() else 1,
            "counterparty_id": self.counterparty_combo.currentData(),
            "items": items,
        }
