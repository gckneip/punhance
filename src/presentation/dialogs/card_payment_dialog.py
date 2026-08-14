from typing import List
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDateEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QLabel, QMessageBox, QDialogButtonBox,
)
from PySide6.QtCore import QDate, Qt
from src.application.dto.account_dto import AccountDTO
from src.application.dto.installment_dto import InstallmentDTO


class CardPaymentDialog(QDialog):
    def __init__(
        self,
        accounts: List[AccountDTO],
        installments: List[InstallmentDTO],
        current_debt: float,
        card_name: str,
        parent=None,
    ):
        super().__init__(parent)
        self._accounts = accounts
        self._installments = installments
        self.setWindowTitle(f"Pay Card: {card_name}")
        self.setModal(True)
        self.resize(550, 500)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date:", self.date_edit)

        self.account_combo = QComboBox()
        for acc in accounts:
            self.account_combo.addItem(f"{acc.name} ({acc.type})", acc.id)
        form.addRow("From Account:", self.account_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 999999)
        self.amount_spin.setPrefix("R$ ")
        self.amount_spin.setValue(current_debt)
        form.addRow("Amount:", self.amount_spin)

        self.description_edit = QLineEdit()
        self.description_edit.setText(f"Payment to {card_name}")
        form.addRow("Description:", self.description_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(50)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        if installments:
            inst_label = QLabel("Select installments to pay:")
            inst_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
            layout.addWidget(inst_label)

            self._inst_table = QTableWidget()
            self._inst_table.setColumnCount(4)
            self._inst_table.setHorizontalHeaderLabels(
                ["Pay", "Due Date", "Amount", "Status"]
            )
            self._inst_table.horizontalHeader().setStretchLastSection(True)
            self._inst_table.setSelectionBehavior(QTableWidget.SelectRows)
            self._inst_table.setAlternatingRowColors(True)

            self._inst_table.setRowCount(len(installments))
            for i, inst in enumerate(installments):
                check_item = QTableWidgetItem()
                check_item.setCheckState(
                    Qt.Checked if inst.status in ("pending", "overdue") else Qt.Unchecked
                )
                self._inst_table.setItem(i, 0, check_item)
                self._inst_table.setItem(i, 1, QTableWidgetItem(inst.due_date.isoformat()))
                self._inst_table.setItem(i, 2, QTableWidgetItem(f"R$ {inst.amount:.2f}"))
                self._inst_table.setItem(i, 3, QTableWidgetItem(inst.status))

            self._inst_table.resizeColumnsToContents()
            layout.addWidget(self._inst_table)
        else:
            self._inst_table = None
            layout.addWidget(QLabel("No pending installments for this card."))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.description_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Description is required.")
            return
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
            return
        self.accept()

    def get_data(self):
        installment_ids = []
        if self._inst_table:
            for row in range(self._inst_table.rowCount()):
                item = self._inst_table.item(row, 0)
                if item and item.checkState() == Qt.Checked:
                    inst_id = self._installments[row].id
                    installment_ids.append(inst_id)

        return {
            "event_date": self.date_edit.date().toPython(),
            "description": self.description_edit.text().strip(),
            "amount": self.amount_spin.value(),
            "account_id": self.account_combo.currentData(),
            "installment_ids": installment_ids,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
