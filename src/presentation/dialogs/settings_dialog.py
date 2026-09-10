from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout,
)

from src.domain.entities.app_settings import NavigationStyle
from src.presentation import theme

NAVIGATION_STYLE_CHOICES = [
    (NavigationStyle.TABS, "Tabs (top)"),
    (NavigationStyle.SIDEBAR, "Sidebar (side, collapsible)"),
]


class SettingsDialog(QDialog):
    def __init__(self, current_navigation_style: NavigationStyle, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(380, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.navigation_style_combo = QComboBox()
        for style, label in NAVIGATION_STYLE_CHOICES:
            self.navigation_style_combo.addItem(label, style)
        index = self.navigation_style_combo.findData(current_navigation_style)
        if index >= 0:
            self.navigation_style_combo.setCurrentIndex(index)
        form.addRow("Navigation Style:", self.navigation_style_combo)

        layout.addLayout(form)

        note = QLabel("Restart Finance Manager for a navigation style change to take effect.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> dict:
        return {
            "navigation_style": self.navigation_style_combo.currentData(),
        }
