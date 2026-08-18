from typing import List
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QVBoxLayout,
    QMessageBox,
)
from src.application.dto.category_dto import CategoryDTO


class CategoryDialog(QDialog):
    def __init__(self, categories: List[CategoryDTO], parent=None, category: CategoryDTO = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Category" if category else "Create Category")
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
            if category and cat.id == category.id:
                continue
            self.parent_combo.addItem(cat.name, cat.id)
        form.addRow("Parent:", self.parent_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if category is not None:
            self.name_edit.setText(category.name)
            self.color_edit.setText(category.color or "")
            if category.parent_id:
                index = self.parent_combo.findData(category.parent_id)
                if index >= 0:
                    self.parent_combo.setCurrentIndex(index)

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
