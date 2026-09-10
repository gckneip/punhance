from datetime import date, timedelta

from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout,
)


class HomeBankExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export to HomeBank")
        self.setModal(True)
        self.resize(360, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.credit_cards_check = QCheckBox("Include credit card accounts")
        self.credit_cards_check.setChecked(True)
        form.addRow("", self.credit_cards_check)

        self.recurring_check = QCheckBox("Include recurring events")
        self.recurring_check.setChecked(True)
        form.addRow("", self.recurring_check)

        self.all_time_check = QCheckBox("All time")
        self.all_time_check.setChecked(True)
        self.all_time_check.toggled.connect(self._toggle_date_range)
        form.addRow("", self.all_time_check)

        self.from_edit = QDateEdit(calendarPopup=True)
        self.from_edit.setDate(date.today() - timedelta(days=365))
        self.from_edit.setEnabled(False)
        form.addRow("From:", self.from_edit)

        self.to_edit = QDateEdit(calendarPopup=True)
        self.to_edit.setDate(date.today())
        self.to_edit.setEnabled(False)
        form.addRow("To:", self.to_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Choose File...")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_date_range(self, all_time: bool):
        self.from_edit.setEnabled(not all_time)
        self.to_edit.setEnabled(not all_time)

    def get_data(self) -> dict:
        all_time = self.all_time_check.isChecked()
        return {
            "include_credit_cards": self.credit_cards_check.isChecked(),
            "include_recurring": self.recurring_check.isChecked(),
            "date_from": None if all_time else self.from_edit.date().toPython(),
            "date_to": None if all_time else self.to_edit.date().toPython(),
        }
