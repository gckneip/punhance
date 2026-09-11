from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QMessageBox, QDateEdit, QLabel,
    QPushButton, QWidget,
)
from PySide6.QtCore import QDate
from src.domain.entities.financial_event import EventType
from src.presentation import icons
from src.presentation.dialogs.counterparty_dialog import CounterpartyDialog
from src.presentation.widgets.account_credit_card_selector import AccountCreditCardSelector

TYPE_CHOICES = ["expense", "income", "transfer"]
CURRENCIES = ["BRL", "USD", "EUR", "GBP", "JPY", "ARS", "CAD", "AUD"]


class EventDialog(QDialog):
    def __init__(self, accounts, categories, counterparties, credit_cards, on_create_counterparty, parent=None, event=None, duplicate=False):
        super().__init__(parent)
        self._on_create_counterparty = on_create_counterparty
        if duplicate:
            self.setWindowTitle("Duplicate Event")
        elif event:
            self.setWindowTitle("Edit Event")
        else:
            self.setWindowTitle("Create Financial Event")
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

        self.selector = AccountCreditCardSelector(accounts, credit_cards)
        form.addRow("Account or Credit Card:", self.selector)
        self._selector_label = form.labelForField(self.selector)

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
            self.selector.set_mode(
                AccountCreditCardSelector.MODE_ACCOUNT_ONLY if is_transfer
                else AccountCreditCardSelector.MODE_EITHER
            )
            self._selector_label.setText("Account (Source):" if is_transfer else "Account or Credit Card:")
        self.type_combo.currentTextChanged.connect(_on_type_changed)
        _on_type_changed(self.type_combo.currentText())

        self.counterparty_combo = QComboBox()
        self.counterparty_combo.addItem("None", None)
        for cp in counterparties:
            self.counterparty_combo.addItem(cp.name, cp.id)

        counterparty_row = QWidget()
        counterparty_row_layout = QHBoxLayout(counterparty_row)
        counterparty_row_layout.setContentsMargins(0, 0, 0, 0)
        counterparty_row_layout.addWidget(self.counterparty_combo)
        self._btn_add_counterparty = QPushButton()
        self._btn_add_counterparty.setIcon(icons.icon("fa6s.circle-plus"))
        self._btn_add_counterparty.setFixedWidth(36)
        self._btn_add_counterparty.setToolTip("New counterparty")
        self._btn_add_counterparty.clicked.connect(self._add_counterparty)
        counterparty_row_layout.addWidget(self._btn_add_counterparty)
        form.addRow("Counterparty:", counterparty_row)

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
            self.selector.set_selection(event.account_id, event.credit_card_id)
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
        selector_error = self.selector.validation_error()
        if selector_error:
            QMessageBox.warning(self, "Validation", selector_error)
            return
        if self.type_combo.currentText() == "transfer":
            if self.dest_account_combo.currentData() is None:
                QMessageBox.warning(self, "Validation", "Destination account is required for transfers.")
                return
            if self.dest_account_combo.currentData() == self.selector.account_id():
                QMessageBox.warning(self, "Validation", "Source and destination accounts must differ.")
                return
        self.accept()

    def _add_counterparty(self):
        dialog = CounterpartyDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            new_cp = self._on_create_counterparty(data["name"])
            self.counterparty_combo.addItem(new_cp.name, new_cp.id)
            self.counterparty_combo.setCurrentIndex(self.counterparty_combo.count() - 1)

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
            "account_id": self.selector.account_id(),
            "destination_account_id": self.dest_account_combo.currentData(),
            "credit_card_id": self.selector.credit_card_id(),
            "counterparty_id": self.counterparty_combo.currentData(),
            "currency": self.currency_combo.currentText(),
            "notes": self.notes_edit.text().strip() or None,
        }
