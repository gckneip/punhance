from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QMessageBox,
)
from src.domain.entities.account import AccountType
from src.presentation.i18n import CURRENCY_SYMBOLS, t
from src.presentation.labels import account_type_choices
from src.presentation.widgets.currency_spin_box import CurrencySpinBox


class AccountDialog(QDialog):
    def __init__(self, parent=None, account=None):
        super().__init__(parent)
        self.setWindowTitle(t("account_dialog.title_edit") if account else t("account_dialog.title_create"))
        self.setModal(True)
        self.resize(350, 200)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow(f'{t("common.name")}:', self.name_edit)

        self.type_combo = QComboBox()
        for account_type, label in account_type_choices():
            self.type_combo.addItem(label, account_type)
        form.addRow(f'{t("common.type")}:', self.type_combo)

        self.balance_spin = CurrencySpinBox(allow_negative=True)
        self.balance_spin.setRange(-999999, 999999)
        self.balance_spin.setPrefix(CURRENCY_SYMBOLS["BRL"] + " ")
        form.addRow(t("account_dialog.initial_balance"), self.balance_spin)

        layout.addLayout(form)

        if account is not None:
            self.name_edit.setText(account.name)
            type_value = account.type.value if hasattr(account.type, "value") else account.type
            index = self.type_combo.findData(AccountType(type_value))
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            self.balance_spin.setValue(account.initial_balance)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, t("common.warning"), t("account_dialog.name_required"))
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentData(),
            "initial_balance": self.balance_spin.value(),
        }
