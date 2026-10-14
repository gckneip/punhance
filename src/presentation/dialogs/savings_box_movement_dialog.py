from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QMessageBox, QVBoxLayout,
)

from src.presentation.i18n import CURRENCY_SYMBOLS, t
from src.presentation.widgets.currency_spin_box import CurrencySpinBox


class SavingsBoxMovementDialog(QDialog):
    """Deposit into (aporte) or withdraw from (resgate) a single savings box.

    Deliberately minimal: a savings box moves a plain amount on a date, so this
    asks only for value, date, the optional finance account the cash flows
    through, and a note — no quantity / unit price / fees, which only make sense
    for quantity-priced assets.
    """

    def __init__(self, parent, box, direction, accounts=None):
        super().__init__(parent)
        self._box = box
        self._direction = direction  # "deposit" | "withdraw"
        self._is_out = direction == "withdraw"
        self._accounts = list(accounts or [])

        title_key = (
            "savings_movement.title_withdraw" if self._is_out
            else "savings_movement.title_deposit"
        )
        self.setWindowTitle(t(title_key, name=box.name))
        self.setModal(True)
        self.resize(380, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        currency = getattr(box, "currency", "BRL")
        prefix = CURRENCY_SYMBOLS.get(currency, currency) + " "

        self.amount_spin = CurrencySpinBox()
        self.amount_spin.setRange(0, 999999999)
        self.amount_spin.setPrefix(prefix)
        form.addRow(t("savings_movement.amount"), self.amount_spin)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow(t("common.date"), self.date_edit)

        # Which finance account the cash flows through: a deposit debits it (an
        # outflow into savings), a withdrawal credits it (money coming back).
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
            idx = self.account_combo.findData(getattr(box, "account_id", None))
            if idx >= 0:
                self.account_combo.setCurrentIndex(idx)

        self.notes_edit = QLineEdit()
        form.addRow(t("common.notes"), self.notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if self.amount_spin.value() <= 0:
            QMessageBox.information(
                self, t("common.info"), t("savings_movement.amount_required")
            )
            return
        self.accept()

    def get_data(self):
        return {
            "amount": self.amount_spin.value(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "account_id": self.account_combo.currentData() if self.account_combo else None,
            "notes": self.notes_edit.text().strip() or None,
        }
