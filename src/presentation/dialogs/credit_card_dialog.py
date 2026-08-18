from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox,
    QCheckBox, QDialogButtonBox, QVBoxLayout, QMessageBox,
)


class CreditCardDialog(QDialog):
    def __init__(self, parent=None, card=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Credit Card" if card else "Create Credit Card")
        self.setModal(True)
        self.resize(350, 280)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)

        self.issuer_edit = QLineEdit()
        form.addRow("Issuer:", self.issuer_edit)

        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0, 999999)
        self.limit_spin.setPrefix("R$ ")
        form.addRow("Credit Limit:", self.limit_spin)

        self.closing_spin = QSpinBox()
        self.closing_spin.setRange(1, 28)
        form.addRow("Closing Day:", self.closing_spin)

        self.due_spin = QSpinBox()
        self.due_spin.setRange(1, 28)
        form.addRow("Due Day:", self.due_spin)

        self.active_check = QCheckBox("Active")
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
            QMessageBox.warning(self, "Validation", "Name is required.")
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
