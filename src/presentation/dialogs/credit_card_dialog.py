from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QDialogButtonBox, QVBoxLayout, QMessageBox,
)
from src.presentation.i18n import CURRENCY_SYMBOLS, t
from src.presentation.widgets.currency_spin_box import CurrencySpinBox


class CreditCardDialog(QDialog):
    def __init__(self, parent=None, card=None):
        super().__init__(parent)
        self.setWindowTitle(t("credit_card_dialog.title_edit") if card else t("credit_card_dialog.title_create"))
        self.setModal(True)
        self.resize(350, 280)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow(f'{t("common.name")}:', self.name_edit)

        self.issuer_edit = QLineEdit()
        form.addRow(t("credit_card_dialog.issuer"), self.issuer_edit)

        self.limit_spin = CurrencySpinBox()
        self.limit_spin.setRange(0, 999999)
        self.limit_spin.setPrefix(CURRENCY_SYMBOLS["BRL"] + " ")
        form.addRow(t("credit_card_dialog.credit_limit"), self.limit_spin)

        self.closing_spin = QSpinBox()
        self.closing_spin.setRange(1, 28)
        form.addRow(t("credit_card_dialog.closing_day"), self.closing_spin)

        self.due_spin = QSpinBox()
        self.due_spin.setRange(1, 28)
        form.addRow(t("credit_card_dialog.due_day"), self.due_spin)

        self.active_check = QCheckBox(t("credit_card_dialog.active"))
        self.active_check.setChecked(True)
        form.addRow("", self.active_check)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if card is not None:
            self.name_edit.setText(card.name)
            self.issuer_edit.setText(card.issuer)
            self.limit_spin.setValue(card.credit_limit)
            self.closing_spin.setValue(card.closing_day)
            self.due_spin.setValue(card.due_day)
            self.active_check.setChecked(card.is_active)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, t("common.warning"), t("credit_card_dialog.name_required"))
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "issuer": self.issuer_edit.text().strip(),
            "credit_limit": self.limit_spin.value(),
            "closing_day": self.closing_spin.value(),
            "due_day": self.due_spin.value(),
            "is_active": self.active_check.isChecked(),
        }
