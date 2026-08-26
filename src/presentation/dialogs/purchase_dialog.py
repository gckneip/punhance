from typing import Callable, List
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDateEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
    QCheckBox, QSpinBox, QDialogButtonBox, QWidget, QLayout,
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
        purchase_data=None,
    ):
        super().__init__(parent)
        self._categories = categories
        self._credit_cards = credit_cards
        self._counterparties = counterparties
        self._on_create_counterparty = on_create_counterparty

        self.setWindowTitle("Edit Purchase" if purchase_data else "Create Purchase")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # SetFixedSize (below) sizes the dialog from the layout's sizeHint, which
        # ignores setMinimumWidth on the dialog itself. This zero-height spacer
        # forces that sizeHint to be at least this wide, in both item modes.
        width_spacer = QWidget()
        width_spacer.setFixedHeight(0)
        width_spacer.setMinimumWidth(900)
        layout.addWidget(width_spacer)

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

        self.has_items_check = QCheckBox("Has items")
        self.has_items_check.toggled.connect(self._on_has_items_toggled)
        form.addRow(self.has_items_check)

        self.category_label = QLabel("Category:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("None", None)
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.id)
        form.addRow(self.category_label, self.category_combo)

        layout.addLayout(form)

        self.items_label = QLabel("Items:")
        self.items_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(self.items_label)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["Name", "Qty", "Unit", "Unit Price", "Total", "Category"]
        )
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(180)
        layout.addWidget(self.items_table)

        self.items_btn_row = QWidget()
        btn_row = QHBoxLayout(self.items_btn_row)
        btn_row.setContentsMargins(0, 0, 0, 0)
        self._btn_add_item = QPushButton("+ Add Item")
        self._btn_add_item.clicked.connect(self._add_item_row)
        btn_row.addWidget(self._btn_add_item)
        btn_row.addStretch()
        layout.addWidget(self.items_btn_row)

        self.has_items_check.setChecked(False)
        self._on_has_items_toggled(False)

        if purchase_data is not None:
            self._load_purchase_data(purchase_data)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        layout.setSizeConstraint(QLayout.SetFixedSize)

    def _on_payment_changed(self, method: str):
        self.card_combo.setEnabled(method == "credit_card")

    def _on_installments_toggled(self, checked: bool):
        self.installments_spin.setEnabled(checked)

    def _on_has_items_toggled(self, checked: bool):
        self.category_label.setVisible(not checked)
        self.category_combo.setVisible(not checked)
        self.items_label.setVisible(checked)
        self.items_table.setVisible(checked)
        self.items_btn_row.setVisible(checked)

    def _load_purchase_data(self, purchase_data):
        purchase = purchase_data["purchase"]
        self.date_edit.setDate(QDate(purchase.event_date.year, purchase.event_date.month, purchase.event_date.day))
        self.description_edit.setText(purchase.description or "")
        self.total_spin.setValue(purchase.total_amount)

        payment_index = self.payment_combo.findText(purchase.payment_method)
        if payment_index >= 0:
            self.payment_combo.setCurrentIndex(payment_index)

        card_index = self.card_combo.findData(purchase.credit_card_id)
        if card_index >= 0:
            self.card_combo.setCurrentIndex(card_index)

        installments = purchase_data.get("installments") or []
        if len(installments) > 1:
            self.installments_check.setChecked(True)
            self.installments_spin.setValue(len(installments))

        cp_index = self.counterparty_combo.findData(purchase.counterparty_id)
        if cp_index >= 0:
            self.counterparty_combo.setCurrentIndex(cp_index)

        self.notes_edit.setPlainText(purchase.notes or "")

        items = purchase_data.get("items") or []
        if items:
            for item in items:
                self._add_item_row(
                    name=item.name, qty=item.quantity, unit=item.unit,
                    unit_price=item.unit_price, total=item.total_price,
                    cat_id=item.category_id,
                )
            self.has_items_check.setChecked(True)
        else:
            cat_index = self.category_combo.findData(purchase_data.get("category_id"))
            if cat_index >= 0:
                self.category_combo.setCurrentIndex(cat_index)

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

        def _recalc_total():
            total_spin.setValue(round(qty_spin.value() * price_spin.value(), 2))
        qty_spin.valueChanged.connect(_recalc_total)
        price_spin.valueChanged.connect(_recalc_total)

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
        if self.has_items_check.isChecked():
            items_total = round(sum(
                self.items_table.cellWidget(row, 4).value()
                for row in range(self.items_table.rowCount())
            ), 2)
            total = round(self.total_spin.value(), 2)
            if abs(items_total - total) > 0.01:
                QMessageBox.warning(
                    self,
                    "Validation",
                    f"The items total (R$ {items_total:.2f}) must match the purchase "
                    f"total (R$ {total:.2f}).",
                )
                return
        self.accept()

    def get_data(self):
        items = []
        if self.has_items_check.isChecked():
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
            "category_id": None if self.has_items_check.isChecked() else self.category_combo.currentData(),
            "items": items,
        }
