from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QVBoxLayout,
)

from src.presentation.i18n import CURRENCY_SYMBOLS, format_currency, t
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.presentation.labels import investment_txn_label
from src.domain.entities.investment_transaction import (
    PRINCIPAL_IN_TYPES,
    PRINCIPAL_OUT_TYPES,
)


class InvestActionDialog(QDialog):
    """Record a money-in (invest) or money-out (redeem) movement on a holding,
    with the holding picked inline.

    "Invest" offers the principal-in types (buy / contribution); "redeem" offers
    the principal-out types (sell / withdrawal), so a redemption can be either a
    quantity-priced sale or a plain lump-sum withdrawal. Quantity-priced rows
    auto-compute their total; lump-sum rows (no quantity) take the total as typed.
    """

    def __init__(self, parent, holdings, direction, accounts=None):
        super().__init__(parent)
        self._holdings = list(holdings)
        self._direction = direction  # "invest" | "redeem"
        self._is_out = direction == "redeem"
        self._accounts = list(accounts or [])

        self.setWindowTitle(
            t("invest_action.title_redeem") if self._is_out else t("invest_action.title_invest")
        )
        self.setModal(True)
        self.resize(420, 380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.holding_combo = QComboBox()
        for h in self._holdings:
            self.holding_combo.addItem(h.name, h.id)
        self.holding_combo.currentIndexChanged.connect(self._on_holding_changed)
        form.addRow(t("invest_action.holding"), self.holding_combo)

        self._position_label = QLabel()
        self._position_label.setObjectName("statCardTitle")
        form.addRow("", self._position_label)

        self.type_combo = QComboBox()
        for member in (PRINCIPAL_OUT_TYPES if self._is_out else PRINCIPAL_IN_TYPES):
            self.type_combo.addItem(investment_txn_label(member), member)
        self.type_combo.currentIndexChanged.connect(self._recompute_total)
        form.addRow(t("common.type"), self.type_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow(t("common.date"), self.date_edit)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1_000_000_000)
        self.quantity_spin.setDecimals(6)
        form.addRow(t("investment_transaction_dialog.quantity"), self.quantity_spin)

        self.price_spin = CurrencySpinBox()
        self.price_spin.setRange(0, 99999999)
        form.addRow(t("investment_transaction_dialog.unit_price"), self.price_spin)

        self.fees_spin = CurrencySpinBox()
        self.fees_spin.setRange(0, 99999999)
        form.addRow(t("investment_transaction_dialog.fees"), self.fees_spin)

        self.total_spin = CurrencySpinBox()
        self.total_spin.setRange(0, 999999999)
        form.addRow(t("investment_transaction_dialog.total"), self.total_spin)

        # Which finance account the money moves through: investing debits the
        # account (an investment outflow), redeeming credits it (income) — so
        # the cash actually leaves/lands in Finance.
        self.account_combo = None
        if self._accounts:
            self.account_combo = QComboBox()
            self.account_combo.addItem(t("invest_action.no_account"), None)
            for acc in self._accounts:
                self.account_combo.addItem(acc.name, acc.id)
            account_label = (
                t("invest_action.credit_account") if self._is_out
                else t("invest_action.debit_account")
            )
            form.addRow(account_label, self.account_combo)

        self.notes_edit = QLineEdit()
        form.addRow(t("common.notes"), self.notes_edit)

        layout.addLayout(form)

        self.quantity_spin.valueChanged.connect(self._recompute_total)
        self.price_spin.valueChanged.connect(self._recompute_total)
        self.fees_spin.valueChanged.connect(self._recompute_total)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_holding_changed()

    # -- state ----------------------------------------------------------------

    def _selected_holding(self):
        hid = self.holding_combo.currentData()
        return next((h for h in self._holdings if h.id == hid), None)

    def _on_holding_changed(self):
        holding = self._selected_holding()
        currency = holding.currency if holding else "BRL"
        prefix = CURRENCY_SYMBOLS.get(currency, currency) + " "
        for spin in (self.price_spin, self.fees_spin, self.total_spin):
            spin.setPrefix(prefix)

        if holding is None:
            self._position_label.setText("")
            return
        qty = f"{holding.quantity:g}" if holding.quantity else ""
        value = format_currency(holding.market_value, currency)
        detail = f"{qty} · {value}" if qty else value
        key = "invest_action.available" if self._is_out else "invest_action.position"
        self._position_label.setText(t(key, detail=detail))
        # A buy defaults its unit price to the holding's current price.
        if not self._is_out and holding.current_price:
            self.price_spin.setValue(holding.current_price)
        # Default the credit account to the holding's linked account, if any.
        if self.account_combo is not None:
            idx = self.account_combo.findData(getattr(holding, "account_id", None))
            if idx >= 0:
                self.account_combo.setCurrentIndex(idx)

    def _recompute_total(self):
        quantity = self.quantity_spin.value()
        if quantity <= 0:
            return  # lump-sum types: total entered manually
        gross = quantity * self.price_spin.value()
        fees = self.fees_spin.value()
        if self._is_out:
            self.total_spin.setValue(max(gross - fees, 0))
        else:
            self.total_spin.setValue(gross + fees)

    # -- accept ---------------------------------------------------------------

    def _on_accept(self):
        if self._selected_holding() is None:
            return
        if self.total_spin.value() <= 0 and self.quantity_spin.value() <= 0:
            QMessageBox.information(self, t("common.info"), t("invest_action.amount_required"))
            return
        self.accept()

    def get_data(self):
        return {
            "investment_id": self.holding_combo.currentData(),
            "txn_type": self.type_combo.currentData(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "quantity": self.quantity_spin.value(),
            "unit_price": self.price_spin.value(),
            "fees": self.fees_spin.value(),
            "total": self.total_spin.value(),
            "notes": self.notes_edit.text().strip() or None,
            "account_id": self.account_combo.currentData() if self.account_combo else None,
        }
