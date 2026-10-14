from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QMessageBox, QDateEdit, QLabel,
    QPushButton, QWidget,
)
from PySide6.QtCore import QDate
from src.domain.entities.financial_event import EventType
from src.presentation import icons
from src.presentation.dialogs.counterparty_dialog import CounterpartyDialog
from src.presentation.widgets.account_credit_card_selector import AccountCreditCardSelector
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.presentation.i18n import t, CURRENCIES
from src.presentation.labels import event_type_label, account_type_label

TYPE_CHOICES = ["expense", "income", "transfer", "investment"]


class EventDialog(QDialog):
    def __init__(self, accounts, categories, counterparties, credit_cards, on_create_counterparty, parent=None, event=None, duplicate=False, investments=None, investment_id=None):
        super().__init__(parent)
        self._on_create_counterparty = on_create_counterparty
        self._investments = list(investments or [])
        if duplicate:
            self.setWindowTitle(t("event_dialog.title.duplicate"))
        elif event:
            self.setWindowTitle(t("event_dialog.title.edit"))
        else:
            self.setWindowTitle(t("event_dialog.title.create"))
        self.setModal(True)
        self.resize(400, 350)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow(f"{t('common.date')}:", self.date_edit)

        self.type_combo = QComboBox()
        type_choices = list(TYPE_CHOICES)
        if event is not None and event.event_type not in type_choices:
            type_choices.append(event.event_type)
        for value in type_choices:
            self.type_combo.addItem(event_type_label(value), value)
        form.addRow(f"{t('common.type')}:", self.type_combo)

        amount_row = QHBoxLayout()
        self.amount_spin = CurrencySpinBox(allow_negative=True)
        self.amount_spin.setRange(-999999, 999999)
        amount_row.addWidget(self.amount_spin)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(CURRENCIES)
        self.currency_combo.setCurrentText("BRL")
        amount_row.addWidget(self.currency_combo)
        form.addRow(f"{t('common.amount')}:", amount_row)

        self.description_edit = QLineEdit()
        form.addRow(f"{t('common.description')}:", self.description_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItem(t("common.none"), None)
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.id)
        form.addRow(f"{t('common.category')}:", self.category_combo)

        self.selector = AccountCreditCardSelector(accounts, credit_cards)
        form.addRow(t("event_dialog.account_or_card"), self.selector)
        self._selector_label = form.labelForField(self.selector)

        self.dest_account_combo = QComboBox()
        self.dest_account_combo.addItem(t("common.none"), None)
        for acc in accounts:
            self.dest_account_combo.addItem(f"{acc.name} ({account_type_label(acc.type)})", acc.id)
        self.dest_account_combo.setVisible(False)
        self.dest_label = QLabel(t("event_dialog.destination_account"))
        self.dest_label.setVisible(False)
        form.addRow(self.dest_label, self.dest_account_combo)

        # Which registered holding an investment event contributes to.
        self.investment_combo = QComboBox()
        self.investment_combo.addItem(t("common.none"), None)
        for inv in self._investments:
            self.investment_combo.addItem(inv.name, inv.id)
        self.investment_combo.setVisible(False)
        self.investment_label = QLabel(t("event_dialog.investment_asset"))
        self.investment_label.setVisible(False)
        form.addRow(self.investment_label, self.investment_combo)

        def _on_type_changed(*_):
            current = self.type_combo.currentData()
            is_transfer = (current == "transfer")
            is_investment = (current == "investment")
            is_card_payment = (current == "card_payment")
            self.dest_account_combo.setVisible(is_transfer)
            self.dest_label.setVisible(is_transfer)
            self.investment_combo.setVisible(is_investment)
            self.investment_label.setVisible(is_investment)
            if is_transfer:
                mode = AccountCreditCardSelector.MODE_ACCOUNT_ONLY
            elif is_card_payment:
                # A card payment leaves a real account AND pays down a card:
                # both sides are required, just like a bank transfer has a
                # source and a destination.
                mode = AccountCreditCardSelector.MODE_BOTH
            else:
                mode = AccountCreditCardSelector.MODE_EITHER
            self.selector.set_mode(mode)
            if is_transfer:
                label = t("event_dialog.account_source")
            elif is_card_payment:
                label = t("event_dialog.account_and_card")
            else:
                label = t("event_dialog.account_or_card")
            self._selector_label.setText(label)
        self._on_type_changed = _on_type_changed
        self.type_combo.currentIndexChanged.connect(_on_type_changed)
        _on_type_changed()

        self.counterparty_combo = QComboBox()
        self.counterparty_combo.addItem(t("common.none"), None)
        for cp in counterparties:
            self.counterparty_combo.addItem(cp.name, cp.id)

        counterparty_row = QWidget()
        counterparty_row_layout = QHBoxLayout(counterparty_row)
        counterparty_row_layout.setContentsMargins(0, 0, 0, 0)
        counterparty_row_layout.addWidget(self.counterparty_combo)
        self._btn_add_counterparty = QPushButton()
        self._btn_add_counterparty.setIcon(icons.icon("fa6s.circle-plus"))
        self._btn_add_counterparty.setFixedWidth(36)
        self._btn_add_counterparty.setToolTip(t("event_dialog.new_counterparty"))
        self._btn_add_counterparty.clicked.connect(self._add_counterparty)
        counterparty_row_layout.addWidget(self._btn_add_counterparty)
        form.addRow(t("event_dialog.counterparty"), counterparty_row)

        self.notes_edit = QLineEdit()
        form.addRow(t("event_dialog.notes"), self.notes_edit)

        layout.addLayout(form)

        if event is not None:
            self.date_edit.setDate(QDate(event.event_date.year, event.event_date.month, event.event_date.day))
            index = self.type_combo.findData(event.event_type)
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
            if investment_id is not None:
                inv_index = self.investment_combo.findData(investment_id)
                if inv_index >= 0:
                    self.investment_combo.setCurrentIndex(inv_index)
            _on_type_changed()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.description_edit.text().strip():
            QMessageBox.warning(self, t("event_dialog.validation.title"), t("event_dialog.validation.description_required"))
            return
        if self.amount_spin.value() == 0:
            QMessageBox.warning(self, t("event_dialog.validation.title"), t("event_dialog.validation.amount_zero"))
            return
        selector_error = self.selector.validation_error()
        if selector_error:
            QMessageBox.warning(self, t("event_dialog.validation.title"), selector_error)
            return
        if self.type_combo.currentData() == "transfer":
            if self.dest_account_combo.currentData() is None:
                QMessageBox.warning(self, t("event_dialog.validation.title"), t("event_dialog.validation.dest_required"))
                return
            if self.dest_account_combo.currentData() == self.selector.account_id():
                QMessageBox.warning(self, t("event_dialog.validation.title"), t("event_dialog.validation.accounts_differ"))
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
        current_type = self.type_combo.currentData()
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
            "investment_id": (
                self.investment_combo.currentData()
                if current_type == "investment" else None
            ),
        }
