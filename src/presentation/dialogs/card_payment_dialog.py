from typing import List
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QTextEdit,
    QVBoxLayout, QMessageBox, QDialogButtonBox,
)
from PySide6.QtCore import QDate
from src.application.dto.account_dto import AccountDTO
from src.presentation.i18n import CURRENCY_SYMBOLS, t
from src.presentation.labels import account_type_label
from src.presentation.widgets.currency_spin_box import CurrencySpinBox


class CardPaymentDialog(QDialog):
    def __init__(
        self,
        accounts: List[AccountDTO],
        current_debt: float,
        card_name: str,
        parent=None,
    ):
        super().__init__(parent)
        self._accounts = accounts
        self.setWindowTitle(t("card_payment.title", name=card_name))
        self.setModal(True)
        self.resize(450, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow(f'{t("common.date")}:', self.date_edit)

        self.account_combo = QComboBox()
        for acc in accounts:
            self.account_combo.addItem(f"{acc.name} ({account_type_label(acc.type)})", acc.id)
        form.addRow(t("card_payment.from_account"), self.account_combo)

        self.amount_spin = CurrencySpinBox()
        self.amount_spin.setRange(0.01, 999999)
        self.amount_spin.setPrefix(CURRENCY_SYMBOLS["BRL"] + " ")
        self.amount_spin.setValue(current_debt)
        form.addRow(f'{t("common.amount")}:', self.amount_spin)

        self.description_edit = QLineEdit()
        self.description_edit.setText(t("card_payment.default_description", name=card_name))
        form.addRow(f'{t("common.description")}:', self.description_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(50)
        form.addRow(t("card_payment.notes"), self.notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.description_edit.text().strip():
            QMessageBox.warning(self, t("common.warning"), t("card_payment.description_required"))
            return
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, t("common.warning"), t("card_payment.amount_positive"))
            return
        self.accept()

    def get_data(self):
        return {
            "event_date": self.date_edit.date().toPython(),
            "description": self.description_edit.text().strip(),
            "amount": self.amount_spin.value(),
            "account_id": self.account_combo.currentData(),
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
