from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QDoubleSpinBox


class CurrencySpinBox(QDoubleSpinBox):
    """QDoubleSpinBox where typed digits shift in from the right (like a
    POS/Nubank amount field): typing 1190 yields 0.01, 0.11, 1.19, 11.90."""

    def __init__(self, parent=None, allow_negative=False):
        super().__init__(parent)
        self.setDecimals(2)
        self._allow_negative = allow_negative
        self._negative = False
        self._pristine = True

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._negative = self.value() < 0
        self._pristine = True

    def keyPressEvent(self, event):
        text = event.text()
        if text.isdigit():
            self._append_digit(int(text))
            event.accept()
            return
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self._remove_last_digit()
            event.accept()
            return
        if self._allow_negative and event.key() == Qt.Key_Minus:
            self._negative = not self._negative
            self._apply(self._current_cents())
            event.accept()
            return
        if event.matches(QKeySequence.Paste):
            for ch in QApplication.clipboard().text():
                if ch.isdigit():
                    self._append_digit(int(ch))
            event.accept()
            return
        if event.key() in (
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Tab, Qt.Key_Backtab,
            Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape,
        ):
            super().keyPressEvent(event)
            return
        event.ignore()

    def _current_cents(self) -> int:
        return round(abs(self.value()) * 100)

    def _append_digit(self, digit: int):
        cents = 0 if self._pristine else self._current_cents()
        self._pristine = False
        self._apply(cents * 10 + digit)

    def _remove_last_digit(self):
        self._apply(self._current_cents() // 10)

    def _apply(self, cents: int):
        cents = min(cents, round(self.maximum() * 100))
        sign = -1 if (self._allow_negative and self._negative) else 1
        self.setValue(sign * cents / 100)
