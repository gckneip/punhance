from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from src.presentation import theme

DEFAULT_PLACEHOLDER_TEXT = "Select options to preview this widget."


class PreviewDrawer(QFrame):
    """Side panel showing a live-rendered preview of a dashboard widget config.

    Compact content (a stat tile, a placeholder message) is centered so it
    doesn't look lost in a tall panel; charts/tables keep filling the space.
    """

    def __init__(self, parent=None, width: int = 300):
        super().__init__(parent)
        self.setObjectName("previewDrawer")
        self.setFixedWidth(width)

        self._content = None

        layout = QVBoxLayout(self)
        self._title_label = QLabel("Preview")
        self._title_label.setStyleSheet(f"font-weight: 600; color: {theme.TEXT_SECONDARY};")
        layout.addWidget(self._title_label)

        self._body = QVBoxLayout()
        layout.addLayout(self._body, stretch=1)

        self.show_placeholder(DEFAULT_PLACEHOLDER_TEXT)

    def set_title(self, title: str):
        self._title_label.setText(title or "Preview")

    def show_placeholder(self, text: str):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._set_content(label, center=True)

    def show_content(self, widget: QWidget, center: bool = False):
        self._set_content(widget, center=center)

    def _set_content(self, widget: QWidget, center: bool):
        while self._body.count():
            item = self._body.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
                child.deleteLater()
        self._content = widget
        if center:
            self._body.addStretch()
        self._body.addWidget(widget)
        if center:
            self._body.addStretch()
