from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QMessageBox, QDateEdit, QLabel,
)
from PySide6.QtCore import QDate
from src.domain.entities.financial_event import EventType

TYPE_CHOICES = ["expense", "income", "transfer"]
CURRENCIES = ["BRL", "USD", "EUR", "GBP", "JPY", "ARS", "CAD", "AUD"]


class EventDialog(QDialog):
    def __init__(self, accounts, categories, counterparties, parent=None, event=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Event" if event else "Create Financial Event")
        self.setModal(True)
        self.resize(400, 350)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date:", self.date_edit)

        self.type_combo = QComboBox()
        type_choices = list(TYPE_CHOICES)
        if event is not None and event.event_type not in type_choices:
            type_choices.append(event.event_type)
        self.type_combo.addItems(type_choices)
        form.addRow("Type:", self.type_combo)

        amount_row = QHBoxLayout()
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(-999999, 999999)
        amount_row.addWidget(self.amount_spin)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(CURRENCIES)
        self.currency_combo.setCurrentText("BRL")
        amount_row.addWidget(self.currency_combo)
        form.addRow("Amount:", amount_row)

        self.description_edit = QLineEdit()
        form.addRow("Description:", self.description_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItem("None", None)
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.id)
        form.addRow("Category:", self.category_combo)

        self.account_combo = QComboBox()
        self.account_combo.addItem("None", None)
        for acc in accounts:
            self.account_combo.addItem(f"{acc.name} ({acc.type})", acc.id)
        form.addRow("Account (Source):", self.account_combo)

        self.dest_account_combo = QComboBox()
        self.dest_account_combo.addItem("None", None)
        for acc in accounts:
            self.dest_account_combo.addItem(f"{acc.name} ({acc.type})", acc.id)
        self.dest_account_combo.setVisible(False)
        self.dest_label = QLabel("Destination Account:")
        self.dest_label.setVisible(False)
        form.addRow(self.dest_label, self.dest_account_combo)

        def _on_type_changed(text):
            is_transfer = (text == "transfer")
            self.dest_account_combo.setVisible(is_transfer)
            self.dest_label.setVisible(is_transfer)
        self.type_combo.currentTextChanged.connect(_on_type_changed)

        self.counterparty_combo = QComboBox()
        self.counterparty_combo.addItem("None", None)
        for cp in counterparties:
            self.counterparty_combo.addItem(cp.name, cp.id)
        form.addRow("Counterparty:", self.counterparty_combo)

        self.notes_edit = QLineEdit()
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        if event is not None:
            self.date_edit.setDate(QDate(event.event_date.year, event.event_date.month, event.event_date.day))
            index = self.type_combo.findText(event.event_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            self.amount_spin.setValue(event.amount)
            self.currency_combo.setCurrentText(event.currency)
            self.description_edit.setText(event.description)
            cat_index = self.category_combo.findData(event.category_id)
            if cat_index >= 0:
                self.category_combo.setCurrentIndex(cat_index)
            acc_index = self.account_combo.findData(event.account_id)
            if acc_index >= 0:
                self.account_combo.setCurrentIndex(acc_index)
            dest_index = self.dest_account_combo.findData(event.destination_account_id)
            if dest_index >= 0:
                self.dest_account_combo.setCurrentIndex(dest_index)
            cp_index = self.counterparty_combo.findData(event.counterparty_id)
            if cp_index >= 0:
                self.counterparty_combo.setCurrentIndex(cp_index)
            self.notes_edit.setText(event.notes or "")
            _on_type_changed(self.type_combo.currentText())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.description_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Description is required.")
            return
        if self.amount_spin.value() == 0:
            QMessageBox.warning(self, "Validation", "Amount cannot be zero.")
            return
        if self.type_combo.currentText() == "transfer":
            if self.dest_account_combo.currentData() is None:
                QMessageBox.warning(self, "Validation", "Destination account is required for transfers.")
                return
            if self.dest_account_combo.currentData() == self.account_combo.currentData():
                QMessageBox.warning(self, "Validation", "Source and destination accounts must differ.")
                return
        self.accept()

    def get_data(self):
        type_map = {
            "expense": EventType.EXPENSE,
            "income": EventType.INCOME,
            "transfer": EventType.TRANSFER,
        }
        current_type = self.type_combo.currentText()
        return {
            "event_type": type_map.get(current_type, EventType(current_type)),
            "event_date": self.date_edit.date().toPython(),
            "description": self.description_edit.text().strip(),
            "amount": self.amount_spin.value(),
            "category_id": self.category_combo.currentData(),
            "account_id": self.account_combo.currentData(),
            "destination_account_id": self.dest_account_combo.currentData(),
            "counterparty_id": self.counterparty_combo.currentData(),
            "currency": self.currency_combo.currentText(),
            "notes": self.notes_edit.text().strip() or None,
        }
