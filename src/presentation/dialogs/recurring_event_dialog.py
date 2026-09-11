from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from src.domain.entities.financial_event import EventType
from src.domain.entities.recurring_event import RecurrenceFrequency
from src.presentation.widgets.account_credit_card_selector import AccountCreditCardSelector
from src.presentation.widgets.currency_spin_box import CurrencySpinBox

# All EventType values except "purchase" - a recurring-confirmed bare
# FinancialEvent has no Purchase row, and main_window._edit_event special-cases
# event_type == "purchase" to route to PurchaseDialog, which would then fail
# to find one.
TYPE_CHOICES = ["expense", "income", "transfer", "card_payment", "loan_payment", "investment", "refund"]
CURRENCIES = ["BRL", "USD", "EUR", "GBP", "JPY", "ARS", "CAD", "AUD"]
FREQUENCY_CHOICES = ["daily", "weekly", "monthly", "yearly"]
WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_LABELS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class RecurringEventDialog(QDialog):
    def __init__(
        self, accounts, categories, counterparties, credit_cards, parent=None, recurring_event=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Recurring Event" if recurring_event else "Create Recurring Event")
        self.setModal(True)
        self.resize(420, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.is_active_check = QCheckBox("Active")
        self.is_active_check.setChecked(True)
        form.addRow(self.is_active_check)

        self.type_combo = QComboBox()
        self.type_combo.addItems(TYPE_CHOICES)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type:", self.type_combo)

        amount_row = QHBoxLayout()
        self.amount_spin = CurrencySpinBox(allow_negative=True)
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

        self.counterparty_combo = QComboBox()
        self.counterparty_combo.addItem("None", None)
        for cp in counterparties:
            self.counterparty_combo.addItem(cp.name, cp.id)
        form.addRow("Counterparty:", self.counterparty_combo)

        self.notes_edit = QLineEdit()
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)
        layout.addWidget(self._build_recurrence_group())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if recurring_event is not None:
            self._load_recurring_event(recurring_event)
        else:
            self._on_type_changed(self.type_combo.currentText())

    def _build_recurrence_group(self) -> QGroupBox:
        group = QGroupBox("Recurrence")
        outer = QVBoxLayout(group)
        form = QFormLayout()

        self.frequency_combo = QComboBox()
        for value in FREQUENCY_CHOICES:
            self.frequency_combo.addItem(value.capitalize(), value)
        self.frequency_combo.currentIndexChanged.connect(self._on_frequency_changed)
        form.addRow("Frequency:", self.frequency_combo)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 365)
        self.interval_spin.setValue(1)
        form.addRow("Every:", self.interval_spin)

        self.anchor_stack = QStackedWidget()
        self.anchor_stack.addWidget(QWidget())  # daily: no extra anchor field needed

        weekly_panel = QWidget()
        weekly_form = QFormLayout(weekly_panel)
        self.weekday_combo = QComboBox()
        for i, name in enumerate(WEEKDAY_LABELS):
            self.weekday_combo.addItem(name, i)
        weekly_form.addRow("Day of week:", self.weekday_combo)
        self.anchor_stack.addWidget(weekly_panel)

        monthly_panel = QWidget()
        monthly_form = QFormLayout(monthly_panel)
        self.day_of_month_spin = QSpinBox()
        self.day_of_month_spin.setRange(1, 31)
        self.day_of_month_spin.setValue(1)
        monthly_form.addRow("Day of month:", self.day_of_month_spin)
        self.anchor_stack.addWidget(monthly_panel)

        yearly_panel = QWidget()
        yearly_form = QFormLayout(yearly_panel)
        self.month_combo = QComboBox()
        for i, name in enumerate(MONTH_LABELS, start=1):
            self.month_combo.addItem(name, i)
        yearly_form.addRow("Month:", self.month_combo)
        self.yearly_day_spin = QSpinBox()
        self.yearly_day_spin.setRange(1, 31)
        self.yearly_day_spin.setValue(1)
        yearly_form.addRow("Day:", self.yearly_day_spin)
        self.anchor_stack.addWidget(yearly_panel)

        form.addRow(self.anchor_stack)
        outer.addLayout(form)

        date_form = QFormLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        date_form.addRow("Start date:", self.start_date_edit)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setEnabled(False)

        self.no_end_check = QCheckBox("No end date")
        self.no_end_check.setChecked(True)
        self.no_end_check.toggled.connect(lambda checked: self.end_date_edit.setEnabled(not checked))
        date_form.addRow(self.no_end_check)
        date_form.addRow("End date:", self.end_date_edit)

        outer.addLayout(date_form)
        return group

    def _on_frequency_changed(self, index: int):
        # Stack page order (daily/weekly/monthly/yearly) matches FREQUENCY_CHOICES order.
        self.anchor_stack.setCurrentIndex(index)

    def _on_type_changed(self, text: str):
        is_transfer = (text == "transfer")
        is_card_payment = (text == "card_payment")
        self.dest_account_combo.setVisible(is_transfer)
        self.dest_label.setVisible(is_transfer)
        if is_transfer:
            mode = AccountCreditCardSelector.MODE_ACCOUNT_ONLY
            label = "Account (Source):"
        elif is_card_payment:
            mode = AccountCreditCardSelector.MODE_BOTH
            label = "Account & Credit Card:"
        else:
            mode = AccountCreditCardSelector.MODE_EITHER
            label = "Account or Credit Card:"
        self.selector.set_mode(mode)
        self._selector_label.setText(label)

    def _load_recurring_event(self, r):
        self.is_active_check.setChecked(r.is_active)
        index = self.type_combo.findText(r.event_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        self._on_type_changed(self.type_combo.currentText())
        self.amount_spin.setValue(r.amount)
        self.currency_combo.setCurrentText(r.currency)
        self.description_edit.setText(r.description)
        cat_index = self.category_combo.findData(r.category_id)
        if cat_index >= 0:
            self.category_combo.setCurrentIndex(cat_index)
        self.selector.set_selection(r.account_id, r.credit_card_id)
        dest_index = self.dest_account_combo.findData(r.destination_account_id)
        if dest_index >= 0:
            self.dest_account_combo.setCurrentIndex(dest_index)
        cp_index = self.counterparty_combo.findData(r.counterparty_id)
        if cp_index >= 0:
            self.counterparty_combo.setCurrentIndex(cp_index)
        self.notes_edit.setText(r.notes or "")

        freq_index = self.frequency_combo.findData(r.frequency)
        if freq_index >= 0:
            self.frequency_combo.setCurrentIndex(freq_index)
        self._on_frequency_changed(self.frequency_combo.currentIndex())
        self.interval_spin.setValue(r.interval)
        if r.weekday is not None:
            self.weekday_combo.setCurrentIndex(r.weekday)
        if r.day_of_month is not None:
            self.day_of_month_spin.setValue(r.day_of_month)
            self.yearly_day_spin.setValue(r.day_of_month)
        if r.month is not None:
            month_index = self.month_combo.findData(r.month)
            if month_index >= 0:
                self.month_combo.setCurrentIndex(month_index)
        self.start_date_edit.setDate(QDate(r.start_date.year, r.start_date.month, r.start_date.day))
        if r.end_date is not None:
            self.no_end_check.setChecked(False)
            self.end_date_edit.setDate(QDate(r.end_date.year, r.end_date.month, r.end_date.day))
        else:
            self.no_end_check.setChecked(True)

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
        if not self.no_end_check.isChecked() and self.end_date_edit.date() < self.start_date_edit.date():
            QMessageBox.warning(self, "Validation", "End date must be on or after the start date.")
            return
        self.accept()

    def get_data(self) -> dict:
        frequency_value = self.frequency_combo.currentData()
        day_of_month = None
        weekday = None
        month = None
        if frequency_value == "weekly":
            weekday = self.weekday_combo.currentData()
        elif frequency_value == "monthly":
            day_of_month = self.day_of_month_spin.value()
        elif frequency_value == "yearly":
            month = self.month_combo.currentData()
            day_of_month = self.yearly_day_spin.value()

        return {
            "event_type": EventType(self.type_combo.currentText()),
            "description": self.description_edit.text().strip(),
            "amount": self.amount_spin.value(),
            "frequency": RecurrenceFrequency(frequency_value),
            "interval": self.interval_spin.value(),
            "day_of_month": day_of_month,
            "weekday": weekday,
            "month": month,
            "start_date": self.start_date_edit.date().toPython(),
            "end_date": None if self.no_end_check.isChecked() else self.end_date_edit.date().toPython(),
            "is_active": self.is_active_check.isChecked(),
            "category_id": self.category_combo.currentData(),
            "account_id": self.selector.account_id(),
            "destination_account_id": self.dest_account_combo.currentData(),
            "credit_card_id": self.selector.credit_card_id(),
            "counterparty_id": self.counterparty_combo.currentData(),
            "currency": self.currency_combo.currentText(),
            "notes": self.notes_edit.text().strip() or None,
        }
