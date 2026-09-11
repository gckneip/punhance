from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QMessageBox,
)
from src.domain.entities.account import AccountType
from src.presentation.widgets.currency_spin_box import CurrencySpinBox


class AccountDialog(QDialog):
    def __init__(self, parent=None, account=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Account" if account else "Create Account")
        self.setModal(True)
        self.resize(350, 200)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        for account_type in AccountType:
            self.type_combo.addItem(account_type.value, account_type)
        form.addRow("Type:", self.type_combo)

        self.balance_spin = CurrencySpinBox(allow_negative=True)
        self.balance_spin.setRange(-999999, 999999)
        self.balance_spin.setPrefix("R$ ")
        form.addRow("Initial Balance:", self.balance_spin)

        layout.addLayout(form)

        if account is not None:
            self.name_edit.setText(account.name)
            index = self.type_combo.findText(account.type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            self.balance_spin.setValue(account.initial_balance)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentData(),
            "initial_balance": self.balance_spin.value(),
        }
