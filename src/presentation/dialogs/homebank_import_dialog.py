from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QListWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from src.presentation.i18n import t

# Machine keys for plan_dto.counts; display labels are translated at call time.
_COUNT_KEYS = [
    "accounts",
    "credit_cards",
    "categories",
    "counterparties",
    "events",
    "transfers",
    "purchases",
    "recurring_events",
    "skipped_operations",
]


class HomeBankImportPreviewDialog(QDialog):
    def __init__(self, plan_dto, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("homebank_import.title"))
        self.setModal(True)
        self.resize(520, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(t("homebank_import.intro")))

        table = QTableWidget(len(_COUNT_KEYS), 2)
        table.setHorizontalHeaderLabels([t("homebank_import.col_item"), t("homebank_import.col_count")])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for row, key in enumerate(_COUNT_KEYS):
            table.setItem(row, 0, QTableWidgetItem(t(f"homebank_import.count.{key}")))
            table.setItem(row, 1, QTableWidgetItem(str(plan_dto.counts.get(key, 0))))
        table.setMaximumHeight(300)
        layout.addWidget(table)

        if plan_dto.warnings:
            layout.addWidget(QLabel(t("homebank_import.warnings", count=len(plan_dto.warnings))))
            warnings_list = QListWidget()
            warnings_list.addItems(plan_dto.warnings)
            layout.addWidget(warnings_list)
        else:
            layout.addWidget(QLabel(t("homebank_import.no_warnings")))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(t("homebank_import.import_button"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
