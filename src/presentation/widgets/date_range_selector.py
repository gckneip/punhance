from datetime import timedelta
from typing import Optional

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QHBoxLayout, QMenu, QSizePolicy, QToolButton, QWidget,
)

from src.domain.services.chart_data_service import ChartDataService, DateRangeSpec
from src.presentation import icons

# (label, spec dict) - spec is None for the "Custom Range..." sentinel, which
# reveals the two QDateEdit pickers instead of resolving to a fixed dict.
PRESETS = [
    ("Last Month", {"mode": "rolling", "unit": "months", "amount": 1}),
    ("Last 3 Months", {"mode": "rolling", "unit": "months", "amount": 3}),
    ("Last 6 Months", {"mode": "rolling", "unit": "months", "amount": 6}),
    ("This Month", {"mode": "calendar", "period": "month", "offset": 0}),
    ("This Year", {"mode": "calendar", "period": "year", "offset": 0}),
    ("Last Year", {"mode": "rolling", "unit": "months", "amount": 12}),
    ("All Time", {"mode": "fixed", "date_from": None, "date_to": None}),
    ("Custom Range...", None),
]

_CUSTOM_INDEX = len(PRESETS) - 1


def find_preset_index(range_dict: Optional[dict]) -> Optional[int]:
    if not range_dict:
        return None
    for index, (_, spec) in enumerate(PRESETS):
        if spec is not None and spec == range_dict:
            return index
    return None


class DateRangeSelector(QWidget):
    """Reusable preset date-range picker: common presets (Last Month, Last 3
    Months, ...) plus a Custom Range option that reveals From/To date
    pickers. Emits a DateRangeSpec-compatible dict whenever the effective
    range changes.

    In `compact` mode (for cramped spots like a dashboard widget's header)
    the preset list is a small calendar icon button with a dropdown menu
    instead of a full QComboBox, so a long widget title still has room to
    show next to it."""

    range_changed = Signal(dict)

    def __init__(self, parent=None, default_label: str = "Last 3 Months", compact: bool = False):
        super().__init__(parent)
        self._compact = compact
        # Fixed vertically so this never competes for leftover vertical space
        # in a parent QVBoxLayout (e.g. a toolbar row next to a chart that
        # should get all of it) - this is a compact control, not a filler.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._current_index = next(
            (i for i, (label, _) in enumerate(PRESETS) if label == default_label), 0
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._combo = None
        self._button = None
        if compact:
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
        else:
            self._combo = QComboBox()
            self._combo.addItems([label for label, _ in PRESETS])
            self._combo.setMaximumWidth(150)
            self._combo.setCurrentIndex(self._current_index)
            self._combo.currentIndexChanged.connect(self._select_index)
            layout.addWidget(self._combo)

        self._from_edit = QDateEdit(calendarPopup=True)
        self._from_edit.setDisplayFormat("yyyy-MM-dd")
        self._from_edit.setDate(QDate.currentDate().addMonths(-3))
        self._from_edit.setMaximumWidth(110)
        layout.addWidget(self._from_edit)

        self._to_edit = QDateEdit(calendarPopup=True)
        self._to_edit.setDisplayFormat("yyyy-MM-dd")
        self._to_edit.setDate(QDate.currentDate())
        self._to_edit.setMaximumWidth(110)
        layout.addWidget(self._to_edit)

        self._from_edit.dateChanged.connect(self._on_custom_changed)
        self._to_edit.dateChanged.connect(self._on_custom_changed)

        self._update_custom_visibility()

    def _is_custom(self) -> bool:
        return PRESETS[self._current_index][1] is None

    def _update_custom_visibility(self):
        is_custom = self._is_custom()
        self._from_edit.setVisible(is_custom)
        self._to_edit.setVisible(is_custom)

    def _select_index(self, index: int):
        self._current_index = index
        if self._button is not None:
            self._button.setToolTip(PRESETS[index][0])
        self._update_custom_visibility()
        self.range_changed.emit(self.date_range_dict())

    def _on_custom_changed(self, _qdate):
        if self._is_custom():
            self.range_changed.emit(self.date_range_dict())

    def date_range_dict(self) -> dict:
        if self._is_custom():
            return {
                "mode": "fixed",
                "date_from": self._from_edit.date().toPython().isoformat(),
                "date_to": self._to_edit.date().toPython().isoformat(),
            }
        return dict(PRESETS[self._current_index][1])

    def resolved_range(self):
        """Returns (date_from, date_to) as concrete dates, date_to inclusive."""
        spec = DateRangeSpec.from_dict(self.date_range_dict())
        date_from, date_to = ChartDataService.resolve_date_range(spec)
        if date_to is not None:
            date_to = date_to - timedelta(days=1)
        return date_from, date_to

    def set_range_dict(self, range_dict: Optional[dict]):
        """Best-effort restore: selects the matching preset, or falls back to
        Custom Range with the resolved concrete from/to dates."""
        index = find_preset_index(range_dict)
        if index is not None:
            self._set_current_index_silently(index)
            self._update_custom_visibility()
            return

        self._set_current_index_silently(_CUSTOM_INDEX)

        date_from = date_to = None
        if range_dict:
            try:
                spec = DateRangeSpec.from_dict(range_dict)
                date_from, date_to = ChartDataService.resolve_date_range(spec)
                if date_to is not None:
                    date_to = date_to - timedelta(days=1)
            except (ValueError, TypeError):
                pass

        self._from_edit.blockSignals(True)
        self._to_edit.blockSignals(True)
        if date_from is not None:
            self._from_edit.setDate(QDate(date_from.year, date_from.month, date_from.day))
        if date_to is not None:
            self._to_edit.setDate(QDate(date_to.year, date_to.month, date_to.day))
        self._from_edit.blockSignals(False)
        self._to_edit.blockSignals(False)
        self._update_custom_visibility()

    def _set_current_index_silently(self, index: int):
        self._current_index = index
        if self._combo is not None:
            self._combo.blockSignals(True)
            self._combo.setCurrentIndex(index)
            self._combo.blockSignals(False)
        if self._button is not None:
            self._button.setToolTip(PRESETS[index][0])
