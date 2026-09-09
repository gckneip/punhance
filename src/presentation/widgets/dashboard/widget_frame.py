from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.presentation import icons, theme

DASHBOARD_WIDGET_MIME = "application/x-dashboard-widget-id"


def encode_drag_payload(widget_id: str, row_span: int, col_span: int) -> bytes:
    return f"{widget_id}|{row_span}|{col_span}".encode()


def decode_drag_payload(data) -> "tuple[str, int, int]":
    widget_id, row_span, col_span = bytes(data).decode().split("|")
    return widget_id, int(row_span), int(col_span)


class _DragHandle(QLabel):
    def __init__(self, frame: "WidgetFrame", parent=None):
        super().__init__(parent)
        self._frame = frame
        self.setPixmap(icons.icon("fa6s.grip-vertical", color=theme.TEXT_SECONDARY).pixmap(14, 14))
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Drag to move this widget - drop on empty space to move, or onto another widget to swap")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            payload = encode_drag_payload(self._frame.widget_id(), self._frame.row_span(), self._frame.col_span())
            mime.setData(DASHBOARD_WIDGET_MIME, payload)
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
        super().mousePressEvent(event)


class _ResizeHandle(QWidget):
    """Bottom-right corner grip: drag to resize the owning WidgetFrame's grid span."""

    def __init__(self, frame: "WidgetFrame"):
        super().__init__(frame)
        self._frame = frame
        self.setFixedSize(14, 14)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setToolTip("Drag to resize")
        self._dragging = False
        self._start_pos = None
        self._start_row_span = 1
        self._start_col_span = 1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(theme.TEXT_SECONDARY))
        pen.setWidth(2)
        painter.setPen(pen)
        for offset in (4, 8, 12):
            painter.drawLine(self.width() - offset, self.height() - 2, self.width() - 2, self.height() - offset)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = True
        self._start_pos = event.globalPosition().toPoint()
        self._start_row_span = self._frame.row_span()
        self._start_col_span = self._frame.col_span()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        delta = event.globalPosition().toPoint() - self._start_pos
        col_unit_px = max(self._frame.width() / max(self._start_col_span, 1), 1)
        row_unit_px = max(self._frame.height() / max(self._start_row_span, 1), 1)
        new_col_span = min(max(self._start_col_span + round(delta.x() / col_unit_px), 1), 12)
        new_row_span = min(max(self._start_row_span + round(delta.y() / row_unit_px), 1), 8)
        self._frame.preview_span(new_row_span, new_col_span)

    def mouseReleaseEvent(self, event):
        if not self._dragging:
            return
        self._dragging = False
        self._frame.commit_span()


class WidgetFrame(QFrame):
    delete_requested = Signal(str)
    span_changed = Signal(str, int, int)  # widget_id, row_span, col_span
    resize_preview = Signal(str, int, int)  # widget_id, row_span, col_span (live, while dragging)

    def __init__(self, widget_id: str, title: str, content: QWidget, row_span: int, col_span: int, parent=None):
        super().__init__(parent)
        self._widget_id = widget_id
        self._content = None
        self.setObjectName("dashboardWidgetFrame")

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(4)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)

        # The drag handle is edit-only chrome; the title stays visible always
        # so section headings ("Recent Events", ...) aren't lost outside edit mode.
        # Drag-and-drop itself is handled by the grid container (see
        # dashboard_grid_widget.py) so drops work both on empty space and on
        # other widgets - this frame doesn't accept drops itself.
        self._drag_handle = _DragHandle(self)
        header_layout.addWidget(self._drag_handle)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {theme.TEXT_SECONDARY};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self._chrome = QWidget()
        chrome_layout = QHBoxLayout(self._chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)

        chrome_layout.addWidget(QLabel("Rows:"))
        self._row_span_spin = QSpinBox()
        self._row_span_spin.setRange(1, 8)
        self._row_span_spin.setValue(row_span)
        self._row_span_spin.valueChanged.connect(self._emit_span_changed)
        chrome_layout.addWidget(self._row_span_spin)

        chrome_layout.addWidget(QLabel("Cols:"))
        self._col_span_spin = QSpinBox()
        self._col_span_spin.setRange(1, 12)
        self._col_span_spin.setValue(col_span)
        self._col_span_spin.valueChanged.connect(self._emit_span_changed)
        chrome_layout.addWidget(self._col_span_spin)

        delete_btn = QPushButton()
        delete_btn.setIcon(icons.icon("fa6s.xmark", color=theme.EXPENSE))
        delete_btn.setToolTip("Delete widget")
        delete_btn.setFixedWidth(28)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._widget_id))
        chrome_layout.addWidget(delete_btn)

        header_layout.addWidget(self._chrome)

        self._outer.addWidget(header)
        self._drag_handle.setVisible(False)
        self._chrome.setVisible(False)
        self.set_content(content)

        self._resize_handle = _ResizeHandle(self)
        self._resize_handle.setVisible(False)
        self._reposition_resize_handle()

    def widget_id(self) -> str:
        return self._widget_id

    def row_span(self) -> int:
        return self._row_span_spin.value()

    def col_span(self) -> int:
        return self._col_span_spin.value()

    def set_edit_mode(self, enabled: bool):
        self._chrome.setVisible(enabled)
        self._drag_handle.setVisible(enabled)
        self._resize_handle.setVisible(enabled)

    def set_drop_highlight(self, valid):
        """Highlights this frame as a swap target while something is being
        dragged over it - a plain overlay rect would be invisible here since
        this frame paints an opaque background on top of the grid behind it."""
        if valid is None:
            self.setStyleSheet("")
        elif valid:
            self.setStyleSheet(f"QFrame#dashboardWidgetFrame {{ border: 2px dashed {theme.INCOME}; }}")
        else:
            self.setStyleSheet(f"QFrame#dashboardWidgetFrame {{ border: 2px dashed {theme.EXPENSE}; }}")

    def set_span_values(self, row_span: int, col_span: int):
        self._row_span_spin.blockSignals(True)
        self._col_span_spin.blockSignals(True)
        self._row_span_spin.setValue(row_span)
        self._col_span_spin.setValue(col_span)
        self._row_span_spin.blockSignals(False)
        self._col_span_spin.blockSignals(False)

    def preview_span(self, row_span: int, col_span: int):
        """Live feedback while dragging the resize handle - updates the
        spinbox numbers and emits resize_preview for a grid overlay highlight,
        without touching the actual grid layout (too expensive to redo on
        every mouse move)."""
        self.set_span_values(row_span, col_span)
        self.resize_preview.emit(self._widget_id, row_span, col_span)

    def commit_span(self):
        self._emit_span_changed()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_resize_handle()

    def _reposition_resize_handle(self):
        if not hasattr(self, "_resize_handle"):
            return
        margin = 2
        x = max(self.width() - self._resize_handle.width() - margin, 0)
        y = max(self.height() - self._resize_handle.height() - margin, 0)
        self._resize_handle.move(x, y)
        self._resize_handle.raise_()

    def set_content(self, content: QWidget):
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.setParent(None)
            self._content.deleteLater()
        self._content = content
        self._outer.addWidget(content, stretch=1)

    def _emit_span_changed(self):
        self.span_changed.emit(self._widget_id, self._row_span_spin.value(), self._col_span_spin.value())
