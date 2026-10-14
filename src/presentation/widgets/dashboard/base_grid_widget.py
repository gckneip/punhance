from typing import Dict, List, Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from src.application.dto.dashboard_widget_dto import (
    CreateDashboardWidgetDTO, DashboardWidgetLayoutUpdateDTO,
)
from src.presentation import icons, theme
from src.presentation.i18n import t
from src.presentation.labels import localize_default_title
from src.presentation.widgets.dashboard.widget_frame import (
    DASHBOARD_WIDGET_MIME, WidgetFrame, decode_drag_payload,
)

GRID_COLUMNS = 12
GRID_SPACING = 12
ROW_UNIT_PX = 64


class _GridBackground(QWidget):
    """Grid container that paints a dotted column/row guide in edit mode, and
    is the sole drag/drop target for moving widgets - accepting drops both on
    empty space and on top of other widgets (frames themselves don't accept
    drops, so Qt delivers the events here regardless of what's under the
    cursor)."""

    move_requested = Signal(str, int, int)  # widget_id, target_row, target_col
    preview_changed = Signal(object)  # (row, col, row_span, col_span, fits) or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._show_grid = False
        self._preview = None  # (row, col, row_span, col_span, fits)
        self._fit_checker = None
        self.setAcceptDrops(True)

    def set_show_grid(self, show: bool):
        self._show_grid = show
        self.update()

    def set_fit_checker(self, fn):
        self._fit_checker = fn

    def set_preview(self, preview):
        """Sets the overlay rect directly - used for resize-drag previews,
        which aren't driven by a native drag-and-drop event."""
        self._preview = preview
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DASHBOARD_WIDGET_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(DASHBOARD_WIDGET_MIME):
            return
        widget_id, row_span, col_span = decode_drag_payload(event.mimeData().data(DASHBOARD_WIDGET_MIME))
        row, col = self._cell_at(event.position().toPoint())
        col = max(min(col, GRID_COLUMNS - col_span), 0)
        fits = self._fit_checker(widget_id, row, col, row_span, col_span) if self._fit_checker else True
        self._preview = (row, col, row_span, col_span, fits)
        self.update()
        self.preview_changed.emit(self._preview)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._preview = None
        self.update()
        self.preview_changed.emit(None)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(DASHBOARD_WIDGET_MIME):
            widget_id, row_span, col_span = decode_drag_payload(event.mimeData().data(DASHBOARD_WIDGET_MIME))
            row, col = self._cell_at(event.position().toPoint())
            col = max(min(col, GRID_COLUMNS - col_span), 0)
            self.move_requested.emit(widget_id, row, col)
        self._preview = None
        self.update()
        self.preview_changed.emit(None)
        event.acceptProposedAction()

    def _cell_at(self, pos: QPoint) -> "tuple[int, int]":
        layout = self.layout()
        if layout is None:
            return 0, 0

        col = GRID_COLUMNS - 1
        for c in range(GRID_COLUMNS):
            rect = layout.cellRect(0, c)
            if rect.isValid() and pos.x() < rect.right():
                col = c
                break

        row_count = max(layout.rowCount(), 1)
        row = row_count  # past the last row = a new row at the bottom
        for r in range(row_count):
            rect = layout.cellRect(r, 0)
            if rect.isValid() and pos.y() < rect.bottom():
                row = r
                break
        return row, col

    def _row_y_bounds(self, row: int) -> "tuple[float, float]":
        layout = self.layout()
        rect = layout.cellRect(row, 0)
        if rect.isValid():
            return rect.top(), rect.bottom()
        # Row doesn't exist in the layout yet (previewing a drop below the
        # last row) - extrapolate its position from the last real row.
        last_row = max(layout.rowCount() - 1, 0)
        last_rect = layout.cellRect(last_row, 0)
        base = last_rect.bottom() if last_rect.isValid() else 0
        unit = ROW_UNIT_PX + GRID_SPACING
        top = base + GRID_SPACING + (row - last_row - 1) * unit
        return top, top + ROW_UNIT_PX

    def paintEvent(self, event):
        super().paintEvent(event)
        layout = self.layout()
        if layout is None:
            return
        painter = QPainter(self)

        if self._show_grid:
            pen = QPen(QColor(theme.TEXT_SECONDARY))
            pen.setWidth(2)
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)

            # Query the layout's real cell geometry rather than assuming
            # uniform spacing math, so the lines land exactly in the gaps
            # between widgets (and stay accurate regardless of margins/spacing).
            height = self.height()
            for col in range(GRID_COLUMNS - 1):
                rect, next_rect = layout.cellRect(0, col), layout.cellRect(0, col + 1)
                if rect.isValid() and next_rect.isValid():
                    x = round((rect.right() + next_rect.left()) / 2)
                    painter.drawLine(x, 0, x, height)

            width = self.width()
            for row in range(layout.rowCount() - 1):
                rect, next_rect = layout.cellRect(row, 0), layout.cellRect(row + 1, 0)
                if rect.isValid() and next_rect.isValid():
                    y = round((rect.bottom() + next_rect.top()) / 2)
                    painter.drawLine(0, y, width, y)

        if self._preview is not None:
            row, col, row_span, col_span, fits = self._preview
            left_rect = layout.cellRect(0, col)
            right_rect = layout.cellRect(0, min(col + col_span - 1, GRID_COLUMNS - 1))
            left = left_rect.left() if left_rect.isValid() else 0
            right = right_rect.right() if right_rect.isValid() else self.width()
            top, _ = self._row_y_bounds(row)
            _, bottom = self._row_y_bounds(row + row_span - 1)

            rect = QRect(round(left), round(top), round(right - left), round(bottom - top))
            fill_color = QColor(theme.INCOME if fits else theme.EXPENSE)
            fill_color.setAlpha(50)
            painter.fillRect(rect, fill_color)
            pen = QPen(QColor(theme.INCOME if fits else theme.EXPENSE))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)


def _footprints_overlap(widget, row, col, row_span, col_span) -> bool:
    return not (
        widget.grid_row + widget.grid_row_span <= row
        or row + row_span <= widget.grid_row
        or widget.grid_col + widget.grid_col_span <= col
        or col + col_span <= widget.grid_col
    )


def _occupied_cells(widgets, exclude_ids=()):
    occupied = set()
    for w in widgets:
        if w.id in exclude_ids:
            continue
        for r in range(w.grid_row, w.grid_row + w.grid_row_span):
            for c in range(w.grid_col, w.grid_col + w.grid_col_span):
                occupied.add((r, c))
    return occupied


def _fits(row, col, row_span, col_span, occupied):
    for r in range(row, row + row_span):
        for c in range(col, col + col_span):
            if (r, c) in occupied or c >= GRID_COLUMNS:
                return False
    return True


def find_next_placement(widgets, row_span: int, col_span: int) -> "tuple[int, int]":
    """Shelf-packing: place at the column offering the lowest next-free-row."""
    col_span = min(col_span, GRID_COLUMNS)
    next_free_row = [0] * GRID_COLUMNS
    for w in widgets:
        for c in range(w.grid_col, min(w.grid_col + w.grid_col_span, GRID_COLUMNS)):
            next_free_row[c] = max(next_free_row[c], w.grid_row + w.grid_row_span)

    best_row, best_col = None, None
    for start_col in range(0, GRID_COLUMNS - col_span + 1):
        row_candidate = max(next_free_row[start_col:start_col + col_span])
        if best_row is None or row_candidate < best_row:
            best_row, best_col = row_candidate, start_col
    return best_row or 0, best_col or 0


class BaseGridWidget(QWidget):
    """Data-source-agnostic 12-column dashboard grid: Edit-Layout mode, drag-to-move,
    resize, add/remove widgets, collision handling and layout persistence.

    Subclasses supply the domain-specific seams:
      - ``_build_content(dto)``            : render a widget's content
      - ``_open_add_widget_dialog()``      : the add-widget picker
      - ``_push_data()``                   : (optional) data-only refresh path
      - ``_frame_date_range/_frame_days_ahead(dto)`` : (optional) header selectors
    """

    entry_added = Signal()
    edit_event_requested = Signal(str)

    def __init__(
        self,
        dashboard_layout_use_cases,
        dashboard_id="default",
        dashboard_widget_template_use_cases=None,
        parent=None,
    ):
        super().__init__(parent)
        self._layout_use_cases = dashboard_layout_use_cases
        self._dashboard_id = dashboard_id
        self._widget_template_use_cases = dashboard_widget_template_use_cases

        self._edit_mode = False
        self._widgets: List = []
        self._frames: Dict[str, WidgetFrame] = {}

        self._build_ui()

    # -- subclass seams -------------------------------------------------------

    def _build_content(self, dto) -> QWidget:
        raise NotImplementedError

    def _open_add_widget_dialog(self) -> Optional[dict]:
        """Return a picker result dict {title, config, row_span, col_span,
        source_preset_id} or None if cancelled."""
        raise NotImplementedError

    def _push_data(self):
        """Data-only refresh hook (no structural change). Default: nothing."""
        pass

    def _before_rebuild(self):
        """Hook called at the start of a structural rebuild (after frames are
        cleared), for subclasses to reset per-rebuild caches. Default: nothing."""
        pass

    def _after_rebuild(self):
        """Hook called at the end of a structural rebuild. Default: push data."""
        self._push_data()

    def _frame_date_range(self, dto):
        return None

    def _frame_days_ahead(self, dto):
        return None

    def _on_widget_date_range_changed(self, widget_id: str, date_range: dict):
        pass

    def _on_widget_days_ahead_changed(self, widget_id: str, days_ahead: int):
        pass

    def focus_quick_add(self):
        pass

    # -- shared machinery -----------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        toolbar = QHBoxLayout()
        self._edit_btn = QPushButton(t("dashboard.edit_layout"))
        self._edit_btn.setCheckable(True)
        self._edit_btn.setIcon(icons.icon("fa6s.pen"))
        self._edit_btn.toggled.connect(self._on_edit_toggled)
        toolbar.addWidget(self._edit_btn)

        add_btn = QPushButton(t("dashboard.add_widget"))
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_add_widget)
        toolbar.addWidget(add_btn)
        self._build_extra_toolbar(toolbar)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        self._grid_container = _GridBackground()
        self._grid_container.set_fit_checker(self._check_move_fits)
        self._grid_container.move_requested.connect(self._on_move_widget)
        self._grid_container.preview_changed.connect(self._on_preview_changed)
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(GRID_SPACING)
        for col in range(GRID_COLUMNS):
            self._grid.setColumnStretch(col, 1)
        # Width should always track the scroll area's viewport (so the
        # 12-column grid fills it); height must stay at its natural content
        # size so the scroll area knows when to actually show a scrollbar,
        # instead of stretching the grid to fill a tall-but-sparse window.
        self._grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(self._grid_container)
        outer.addWidget(self._scroll_area, stretch=1)

    def _build_extra_toolbar(self, toolbar):
        """Hook for subclasses to add buttons to the toolbar. Default: nothing."""
        pass

    def _load_widgets(self):
        self._widgets = self._layout_use_cases.list_widgets(self._dashboard_id)

    def _reload_and_rebuild(self):
        self._load_widgets()
        self._rebuild_layout()

    # -- layout structure ----------------------------------------------------

    def _rebuild_layout(self):
        self._grid_container.set_preview(None)
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._frames.clear()
        self._before_rebuild()

        for dto in self._widgets:
            content = self._build_content(dto)
            frame = WidgetFrame(
                dto.id, localize_default_title(dto.title, dto.config), content,
                dto.grid_row_span, dto.grid_col_span,
                date_range=self._frame_date_range(dto), days_ahead=self._frame_days_ahead(dto),
            )
            frame.set_edit_mode(self._edit_mode)
            frame.delete_requested.connect(self._on_delete_widget)
            frame.span_changed.connect(self._on_span_changed)
            frame.resize_preview.connect(self._on_resize_preview)
            frame.date_range_changed.connect(self._on_widget_date_range_changed)
            frame.days_ahead_changed.connect(self._on_widget_days_ahead_changed)
            self._frames[dto.id] = frame
            self._grid.addWidget(frame, dto.grid_row, dto.grid_col, dto.grid_row_span, dto.grid_col_span)

        for row in range(self._grid.rowCount()):
            self._grid.setRowMinimumHeight(row, ROW_UNIT_PX)

        self._after_rebuild()

    # -- edit-mode interactions ------------------------------------------------

    def _on_edit_toggled(self, enabled: bool):
        self._edit_mode = enabled
        self._grid_container.set_show_grid(enabled)
        for frame in self._frames.values():
            frame.set_edit_mode(enabled)

    def _on_delete_widget(self, widget_id: str):
        reply = QMessageBox.question(
            self, t("dashboard.delete_widget.title"), t("dashboard.delete_widget.body"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._layout_use_cases.delete_widget(widget_id)
        self._reload_and_rebuild()

    def _on_resize_preview(self, widget_id: str, row_span: int, col_span: int):
        dto = next((w for w in self._widgets if w.id == widget_id), None)
        if dto is None:
            return
        fits = self._check_move_fits(widget_id, dto.grid_row, dto.grid_col, row_span, col_span)
        preview = (dto.grid_row, dto.grid_col, row_span, col_span, fits)
        self._grid_container.set_preview(preview)
        self._on_preview_changed(preview)

    def _on_span_changed(self, widget_id: str, row_span: int, col_span: int):
        self._grid_container.set_preview(None)
        self._on_preview_changed(None)

        dto = next((w for w in self._widgets if w.id == widget_id), None)
        if dto is None:
            return
        occupied = _occupied_cells(self._widgets, exclude_ids={widget_id})
        if not _fits(dto.grid_row, dto.grid_col, row_span, col_span, occupied):
            frame = self._frames.get(widget_id)
            if frame is not None:
                frame.set_span_values(dto.grid_row_span, dto.grid_col_span)
            return
        self._layout_use_cases.update_layout([
            DashboardWidgetLayoutUpdateDTO(
                id=dto.id, grid_row=dto.grid_row, grid_col=dto.grid_col,
                grid_row_span=row_span, grid_col_span=col_span, sort_order=dto.sort_order,
            )
        ])
        self._reload_and_rebuild()

    def _check_move_fits(self, widget_id: str, row: int, col: int, row_span: int, col_span: int) -> bool:
        others = [w for w in self._widgets if w.id != widget_id]
        occupied = _occupied_cells(others)
        return _fits(row, col, row_span, col_span, occupied)

    def _on_preview_changed(self, preview):
        for frame in self._frames.values():
            frame.set_drop_highlight(None)
        if preview is None:
            return
        row, col, row_span, col_span, fits = preview
        for dto in self._widgets:
            if _footprints_overlap(dto, row, col, row_span, col_span):
                frame = self._frames.get(dto.id)
                if frame is not None:
                    frame.set_drop_highlight(fits)

    def _on_move_widget(self, widget_id: str, target_row: int, target_col: int):
        dto = next((w for w in self._widgets if w.id == widget_id), None)
        if dto is None:
            return
        if dto.grid_row == target_row and dto.grid_col == target_col:
            return

        others = [w for w in self._widgets if w.id != widget_id]
        occupied = _occupied_cells(others)
        if _fits(target_row, target_col, dto.grid_row_span, dto.grid_col_span, occupied):
            self._layout_use_cases.update_layout([
                DashboardWidgetLayoutUpdateDTO(
                    id=dto.id, grid_row=target_row, grid_col=target_col,
                    grid_row_span=dto.grid_row_span, grid_col_span=dto.grid_col_span,
                    sort_order=dto.sort_order,
                )
            ])
            self._reload_and_rebuild()
            return

        # Dropped onto occupied space: swap with the widget occupying it,
        # but only when the drop unambiguously targets a single widget.
        overlapping = [
            w for w in others
            if _footprints_overlap(w, target_row, target_col, dto.grid_row_span, dto.grid_col_span)
        ]
        if len(overlapping) == 1:
            self._on_swap_widgets(widget_id, overlapping[0].id)

    def _on_swap_widgets(self, source_id: str, target_id: str):
        source = next((w for w in self._widgets if w.id == source_id), None)
        target = next((w for w in self._widgets if w.id == target_id), None)
        if source is None or target is None:
            return

        others = [w for w in self._widgets if w.id not in (source_id, target_id)]
        occupied = _occupied_cells(others)
        if not _fits(target.grid_row, target.grid_col, source.grid_row_span, source.grid_col_span, occupied):
            return
        if not _fits(source.grid_row, source.grid_col, target.grid_row_span, target.grid_col_span, occupied):
            return

        self._layout_use_cases.update_layout([
            DashboardWidgetLayoutUpdateDTO(
                id=source.id, grid_row=target.grid_row, grid_col=target.grid_col,
                grid_row_span=source.grid_row_span, grid_col_span=source.grid_col_span,
                sort_order=source.sort_order,
            ),
            DashboardWidgetLayoutUpdateDTO(
                id=target.id, grid_row=source.grid_row, grid_col=source.grid_col,
                grid_row_span=target.grid_row_span, grid_col_span=target.grid_col_span,
                sort_order=target.sort_order,
            ),
        ])
        self._reload_and_rebuild()

    def _on_add_widget(self):
        result = self._open_add_widget_dialog()
        if result is None:
            return

        row, col = find_next_placement(self._widgets, result["row_span"], result["col_span"])
        self._layout_use_cases.add_widget(CreateDashboardWidgetDTO(
            kind="generic",
            title=result["title"],
            grid_row=row,
            grid_col=col,
            grid_row_span=result["row_span"],
            grid_col_span=result["col_span"],
            sort_order=len(self._widgets),
            config=result["config"],
            source_preset_id=result.get("source_preset_id"),
            dashboard_id=self._dashboard_id,
        ))
        self._reload_and_rebuild()
