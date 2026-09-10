from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QListWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

_COUNT_LABELS = [
    ("accounts", "Accounts"),
    ("credit_cards", "Credit Cards"),
    ("categories", "Categories"),
    ("counterparties", "Counterparties"),
    ("events", "Events"),
    ("transfers", "Transfers"),
    ("purchases", "Purchases"),
    ("recurring_events", "Recurring Events"),
    ("skipped_operations", "Skipped Operations"),
]


class HomeBankImportPreviewDialog(QDialog):
    def __init__(self, plan_dto, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from HomeBank - Preview")
        self.setModal(True)
        self.resize(520, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("The following will be created if you continue:"))

        table = QTableWidget(len(_COUNT_LABELS), 2)
        table.setHorizontalHeaderLabels(["Item", "Count"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for row, (key, label) in enumerate(_COUNT_LABELS):
            table.setItem(row, 0, QTableWidgetItem(label))
            table.setItem(row, 1, QTableWidgetItem(str(plan_dto.counts.get(key, 0))))
        table.setMaximumHeight(300)
        layout.addWidget(table)

        if plan_dto.warnings:
            layout.addWidget(QLabel(f"Warnings ({len(plan_dto.warnings)}):"))
            warnings_list = QListWidget()
            warnings_list.addItems(plan_dto.warnings)
            layout.addWidget(warnings_list)
        else:
            layout.addWidget(QLabel("No warnings."))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Import")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
