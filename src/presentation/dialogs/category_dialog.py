from typing import List
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QVBoxLayout,
    QMessageBox,
)
from src.application.dto.category_dto import CategoryDTO


class CategoryDialog(QDialog):
    def __init__(self, categories: List[CategoryDTO], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Category")
        self.setModal(True)
        self.resize(350, 200)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)

        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#ff0000")
        form.addRow("Color:", self.color_edit)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None", None)
        for cat in categories:
            self.parent_combo.addItem(cat.name, cat.id)
        form.addRow("Parent:", self.parent_combo)

        layout.addLayout(form)

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
            "color": self.color_edit.text().strip() or None,
            "parent_id": self.parent_combo.currentData(),
        }
