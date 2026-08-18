from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QVBoxLayout, QMessageBox,
)


class CounterpartyDialog(QDialog):
    def __init__(self, parent=None, counterparty=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Counterparty" if counterparty else "Create Counterparty")
        self.setModal(True)
        self.resize(350, 120)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if counterparty is not None:
            self.name_edit.setText(counterparty.name)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        self.accept()

    def get_data(self):
        return {"name": self.name_edit.text().strip()}
