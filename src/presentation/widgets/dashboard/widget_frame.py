from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from src.presentation import icons, theme
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.dashboard.period_ahead_selector import PeriodAheadSelector

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


class _DeleteButton(QPushButton):
    """Floats over the top-right corner of the widget's own content (no
    layout space reserved for it) instead of living in the header row, so
    edit mode never changes the frame's content size versus outside edit
    mode - edit mode should be a faithful preview of the real layout."""

    def __init__(self, frame: "WidgetFrame"):
        super().__init__(frame)
        self.setIcon(icons.icon("fa6s.xmark", color=theme.EXPENSE))
        self.setToolTip("Delete widget")
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; "
            f"border-radius: 12px; padding: 0px; }}"
        )


class WidgetFrame(QFrame):
    delete_requested = Signal(str)
    span_changed = Signal(str, int, int)  # widget_id, row_span, col_span
    resize_preview = Signal(str, int, int)  # widget_id, row_span, col_span (live, while dragging)
    date_range_changed = Signal(str, dict)  # widget_id, new date_range dict
    days_ahead_changed = Signal(str, int)  # widget_id, new days_ahead value

    def __init__(
        self, widget_id: str, title: str, content: QWidget, row_span: int, col_span: int,
        parent=None, date_range: dict = None, days_ahead: int = None,
    ):
        super().__init__(parent)
        self._widget_id = widget_id
        self._content = None
        self._row_span = row_span
        self._col_span = col_span
        self.setObjectName("dashboardWidgetFrame")

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(4)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)

        # The drag handle is edit-only chrome; the title stays visible always
        # so section headings ("Recent Events", ...) aren't lost outside edit
        # mode. Drag-and-drop itself is handled by the grid container (see
        # dashboard_grid_widget.py) so drops work both on empty space and on
        # other widgets - this frame doesn't accept drops itself.
        self._drag_handle = _DragHandle(self)
        header_layout.addWidget(self._drag_handle)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: 600; color: {theme.TEXT_SECONDARY};")
        # Different widget titles are different lengths ("Monthly Expenses"
        # vs "Net"). A QLabel's default size policy (Preferred, which still
        # carries the Shrink flag) makes Qt's layout engine treat
        # minimumSizeHint() - i.e. "wide enough to show the text unclipped" -
        # as a hard floor; setMinimumWidth(0) does NOT override that (0 is
        # already the unset default, so it's a no-op). Ignored is what
        # actually tells the layout to disregard the text's natural width,
        # so whichever column/row a long-titled widget lands in doesn't get
        # forced wider/taller than the dashboard grid's fixed unit size (see
        # dashboard_grid_widget.py). The label still shows full text when
        # there's room; it just clips instead of pushing the grid around
        # when there isn't.
        title_label.setSizePolicy(QSizePolicy.Ignored, title_label.sizePolicy().verticalPolicy())
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self._date_range_selector = None
        if date_range is not None:
            self._date_range_selector = DateRangeSelector(self, compact=True)
            self._date_range_selector.set_range_dict(date_range)
            self._date_range_selector.range_changed.connect(
                lambda d: self.date_range_changed.emit(self._widget_id, d)
            )
            header_layout.addWidget(self._date_range_selector)

        self._period_ahead_selector = None
        if days_ahead is not None:
            self._period_ahead_selector = PeriodAheadSelector(self)
            self._period_ahead_selector.set_days_ahead(days_ahead)
            self._period_ahead_selector.days_changed.connect(
                lambda days: self.days_ahead_changed.emit(self._widget_id, days)
            )
            header_layout.addWidget(self._period_ahead_selector)

        self._outer.addWidget(header)
        self._drag_handle.setVisible(False)
        self.set_content(content)

        # Both of these are edit-only overlays, positioned absolutely (see
        # _reposition_overlays) so they never take layout space and never
        # change the content area's size - unlike the row/col spinboxes this
        # frame used to show in its header, which did.
        self._resize_handle = _ResizeHandle(self)
        self._resize_handle.setVisible(False)

        self._delete_btn = _DeleteButton(self)
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._widget_id))
        self._delete_btn.setVisible(False)

        self._reposition_overlays()

    def widget_id(self) -> str:
        return self._widget_id

    def row_span(self) -> int:
        return self._row_span

    def col_span(self) -> int:
        return self._col_span

    def set_edit_mode(self, enabled: bool):
        self._drag_handle.setVisible(enabled)
        self._resize_handle.setVisible(enabled)
        self._delete_btn.setVisible(enabled)

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
        self._row_span = row_span
        self._col_span = col_span

    def preview_span(self, row_span: int, col_span: int):
        """Live feedback while dragging the resize handle - emits
        resize_preview for a grid overlay highlight, without touching the
        actual grid layout (too expensive to redo on every mouse move)."""
        self.set_span_values(row_span, col_span)
        self.resize_preview.emit(self._widget_id, row_span, col_span)

    def commit_span(self):
        self.span_changed.emit(self._widget_id, self._row_span, self._col_span)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self):
        margin = 2
        if hasattr(self, "_resize_handle"):
            x = max(self.width() - self._resize_handle.width() - margin, 0)
            y = max(self.height() - self._resize_handle.height() - margin, 0)
            self._resize_handle.move(x, y)
            self._resize_handle.raise_()
        if hasattr(self, "_delete_btn"):
            x = max(self.width() - self._delete_btn.width() - margin, 0)
            self._delete_btn.move(x, margin)
            self._delete_btn.raise_()

    def set_content(self, content: QWidget):
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.setParent(None)
            self._content.deleteLater()
        self._content = content
        self._outer.addWidget(content, stretch=1)
