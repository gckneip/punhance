from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

from src.domain.entities.app_settings import NavigationStyle
from src.presentation import theme
from src.presentation.i18n import SUPPORTED_LANGUAGES, t


def _navigation_style_choices():
    return [
        (NavigationStyle.TABS, t("settings.nav.tabs")),
        (NavigationStyle.SIDEBAR, t("settings.nav.sidebar")),
    ]


class SettingsDialog(QDialog):
    import_theme_requested = Signal()

    def __init__(self, current_navigation_style: NavigationStyle, current_theme_id: str,
                 available_themes, current_base_font_size: int, current_language: str = "en",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("dialog.settings.title"))
        self.setModal(True)
        self.resize(380, 290)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.language_combo = QComboBox()
        for code in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(t(f"language.{code}"), code)
        lang_index = self.language_combo.findData(current_language)
        if lang_index >= 0:
            self.language_combo.setCurrentIndex(lang_index)
        form.addRow(t("settings.language"), self.language_combo)

        self.navigation_style_combo = QComboBox()
        for style, label in _navigation_style_choices():
            self.navigation_style_combo.addItem(label, style)
        index = self.navigation_style_combo.findData(current_navigation_style)
        if index >= 0:
            self.navigation_style_combo.setCurrentIndex(index)
        form.addRow(t("settings.navigation_style"), self.navigation_style_combo)

        self.theme_combo = QComboBox()
        self._populate_theme_combo(current_theme_id, available_themes)
        form.addRow(t("settings.theme"), self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 32)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setValue(current_base_font_size)
        form.addRow(t("settings.font_size"), self.font_size_spin)

        layout.addLayout(form)

        self.import_theme_button = QPushButton(t("settings.import_theme"))
        self.import_theme_button.clicked.connect(self.import_theme_requested.emit)
        layout.addWidget(self.import_theme_button)

        note = QLabel(t("settings.restart_note"))
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
            label = theme_summary.name + (t("settings.theme.custom_suffix") if theme_summary.is_custom else "")
            self.theme_combo.addItem(label, theme_summary.theme_id)
        index = self.theme_combo.findData(selected_theme_id)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

    def select_theme(self, theme_id: str, name: str, all_themes) -> None:
        self._populate_theme_combo(theme_id, all_themes)

    def get_data(self) -> dict:
        return {
            "language": self.language_combo.currentData(),
            "navigation_style": self.navigation_style_combo.currentData(),
            "theme_id": self.theme_combo.currentData(),
            "base_font_size": self.font_size_spin.value(),
        }
