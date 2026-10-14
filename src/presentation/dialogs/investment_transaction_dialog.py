from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDateEdit, QDoubleSpinBox, QLineEdit,
    QDialogButtonBox, QVBoxLayout,
)

from src.presentation.i18n import CURRENCY_SYMBOLS, t
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.presentation.labels import investment_txn_choices
from src.domain.entities.investment_transaction import (
    PRINCIPAL_IN_TYPES,
    PRINCIPAL_OUT_TYPES,
)


class InvestmentTransactionDialog(QDialog):
    def __init__(self, parent=None, transaction=None, currency="BRL"):
        super().__init__(parent)
        self.setWindowTitle(
            t("investment_transaction_dialog.title_edit")
            if transaction
            else t("investment_transaction_dialog.title_create")
        )
        self.setModal(True)
        self.resize(360, 300)
        self._currency = currency

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        for member, label in investment_txn_choices():
            self.type_combo.addItem(label, member)
        form.addRow(t("common.type"), self.type_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow(t("common.date"), self.date_edit)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1_000_000_000)
        self.quantity_spin.setDecimals(6)
        form.addRow(t("investment_transaction_dialog.quantity"), self.quantity_spin)

        prefix = CURRENCY_SYMBOLS.get(currency, currency) + " "

        self.price_spin = CurrencySpinBox()
        self.price_spin.setRange(0, 99999999)
        self.price_spin.setPrefix(prefix)
        form.addRow(t("investment_transaction_dialog.unit_price"), self.price_spin)

        self.fees_spin = CurrencySpinBox()
        self.fees_spin.setRange(0, 99999999)
        self.fees_spin.setPrefix(prefix)
        form.addRow(t("investment_transaction_dialog.fees"), self.fees_spin)

        self.total_spin = CurrencySpinBox()
        self.total_spin.setRange(0, 999999999)
        self.total_spin.setPrefix(prefix)
        form.addRow(t("investment_transaction_dialog.total"), self.total_spin)

        self.notes_edit = QLineEdit()
        form.addRow(t("common.notes"), self.notes_edit)

        layout.addLayout(form)

        # Auto-compute total from quantity x unit price (+/- fees) whenever a
        # quantity is present. Income/cost types (no quantity) keep the total the
        # user types directly.
        self.quantity_spin.valueChanged.connect(self._recompute_total)
        self.price_spin.valueChanged.connect(self._recompute_total)
        self.fees_spin.valueChanged.connect(self._recompute_total)
        self.type_combo.currentIndexChanged.connect(self._recompute_total)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if transaction is not None:
            idx = self.type_combo.findData(transaction.txn_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            qdate = QDate.fromString(transaction.date, "yyyy-MM-dd")
            if qdate.isValid():
                self.date_edit.setDate(qdate)
            self.quantity_spin.setValue(transaction.quantity)
            self.price_spin.setValue(transaction.unit_price)
            self.fees_spin.setValue(transaction.fees)
            self.total_spin.setValue(transaction.total)
            self.notes_edit.setText(transaction.notes or "")

    def _recompute_total(self):
        quantity = self.quantity_spin.value()
        if quantity <= 0:
            return  # income/cost types: total entered manually
        gross = quantity * self.price_spin.value()
        txn_type = self.type_combo.currentData()
        fees = self.fees_spin.value()
        if txn_type in PRINCIPAL_OUT_TYPES:
            self.total_spin.setValue(max(gross - fees, 0))
        elif txn_type in PRINCIPAL_IN_TYPES:
            self.total_spin.setValue(gross + fees)
        else:
            self.total_spin.setValue(gross)

    def get_data(self):
        return {
            "txn_type": self.type_combo.currentData(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "quantity": self.quantity_spin.value(),
            "unit_price": self.price_spin.value(),
            "fees": self.fees_spin.value(),
            "total": self.total_spin.value(),
            "notes": self.notes_edit.text().strip() or None,
        }
