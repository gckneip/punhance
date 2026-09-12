from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QMenu, QSizePolicy, QSpinBox, QToolButton, QWidget

from src.presentation import icons

# (label, days) - days is None for the "Custom..." sentinel, which reveals a
# plain day-count spinbox instead of resolving to a fixed value.
PRESETS = [
    ("Next 7 Days", 7),
    ("Next 14 Days", 14),
    ("Next 30 Days", 30),
    ("Next 60 Days", 60),
    ("Next 90 Days", 90),
    ("Next 6 Months", 182),
    ("Next Year", 365),
    ("Custom...", None),
]

_CUSTOM_INDEX = len(PRESETS) - 1


def _preset_index_for_days(days: int) -> Optional[int]:
    for index, (_, preset_days) in enumerate(PRESETS):
        if preset_days == days:
            return index
    return None


class PeriodAheadSelector(QWidget):
    """Compact "how far into the future" picker for dashboard table widgets
    that list upcoming events (installments, recurring occurrences, or a
    merged view of both) - common day-count presets plus a Custom option
    that reveals a plain spinbox. Emits the effective day count whenever it
    changes."""

    days_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._current_index = 2  # "Next 30 Days"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._button = QToolButton()
        self._button.setIcon(icons.icon("fa6s.calendar-days"))
        self._button.setToolTip(PRESETS[self._current_index][0])
        self._button.setFixedSize(24, 24)
        self._button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self._button)
        for index, (label, _) in enumerate(PRESETS):
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, i=index: self._select_index(i))
        self._button.setMenu(menu)
        layout.addWidget(self._button)

        self._spin = QSpinBox()
        self._spin.setRange(1, 3650)
        self._spin.setValue(30)
        self._spin.setSuffix(" days")
        self._spin.setMaximumWidth(90)
        self._spin.valueChanged.connect(self._on_custom_changed)
        layout.addWidget(self._spin)

        self._update_custom_visibility()

    def _is_custom(self) -> bool:
        return PRESETS[self._current_index][1] is None

    def _update_custom_visibility(self):
        self._spin.setVisible(self._is_custom())

    def _select_index(self, index: int):
        self._current_index = index
        self._button.setToolTip(PRESETS[index][0])
        self._update_custom_visibility()
        self.days_changed.emit(self.days_ahead())

    def _on_custom_changed(self, _value):
        if self._is_custom():
            self.days_changed.emit(self.days_ahead())

    def days_ahead(self) -> int:
        if self._is_custom():
            return self._spin.value()
        return PRESETS[self._current_index][1]

    def set_days_ahead(self, days: Optional[int]):
        """Best-effort restore: selects the matching preset, or falls back to
        Custom with the given day count."""
        index = _preset_index_for_days(days) if days is not None else None
        if index is not None:
            self._current_index = index
            self._button.setToolTip(PRESETS[index][0])
            self._update_custom_visibility()
            return

        self._current_index = _CUSTOM_INDEX
        self._button.setToolTip(PRESETS[_CUSTOM_INDEX][0])
        self._spin.blockSignals(True)
        self._spin.setValue(days or 30)
        self._spin.blockSignals(False)
        self._update_custom_visibility()
