from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

from src.domain.entities.app_settings import NavigationStyle
from src.presentation import theme

NAVIGATION_STYLE_CHOICES = [
    (NavigationStyle.TABS, "Tabs (top)"),
    (NavigationStyle.SIDEBAR, "Sidebar (side, collapsible)"),
]


class SettingsDialog(QDialog):
    import_theme_requested = Signal()

    def __init__(self, current_navigation_style: NavigationStyle, current_theme_id: str,
                 available_themes, current_base_font_size: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(380, 250)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.navigation_style_combo = QComboBox()
        for style, label in NAVIGATION_STYLE_CHOICES:
            self.navigation_style_combo.addItem(label, style)
        index = self.navigation_style_combo.findData(current_navigation_style)
        if index >= 0:
            self.navigation_style_combo.setCurrentIndex(index)
        form.addRow("Navigation Style:", self.navigation_style_combo)

        self.theme_combo = QComboBox()
        self._populate_theme_combo(current_theme_id, available_themes)
        form.addRow("Theme:", self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 32)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setValue(current_base_font_size)
        form.addRow("Font Size:", self.font_size_spin)

        layout.addLayout(form)

        self.import_theme_button = QPushButton("Import Theme...")
        self.import_theme_button.clicked.connect(self.import_theme_requested.emit)
        layout.addWidget(self.import_theme_button)

        note = QLabel("Restart Finance Manager for navigation style, theme, or font size changes to take effect.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: {theme.SMALL_FONT_SIZE}px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_theme_combo(self, selected_theme_id: str, available_themes) -> None:
        self.theme_combo.clear()
        for theme_summary in available_themes:
            label = theme_summary.name + (" (Custom)" if theme_summary.is_custom else "")
            self.theme_combo.addItem(label, theme_summary.theme_id)
        index = self.theme_combo.findData(selected_theme_id)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

    def select_theme(self, theme_id: str, name: str, all_themes) -> None:
        self._populate_theme_combo(theme_id, all_themes)

    def get_data(self) -> dict:
        return {
            "navigation_style": self.navigation_style_combo.currentData(),
            "theme_id": self.theme_combo.currentData(),
            "base_font_size": self.font_size_spin.value(),
        }
