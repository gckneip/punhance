import math
from typing import Dict, List, Optional

import pyqtgraph as pg
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from src.presentation import theme
from src.presentation.i18n import format_currency, format_number, t


def _format_value(
    value: float, value_format: str, decimals: int, currency_code: str, for_axis: bool = False
) -> str:
    """Format a chart value per the widget's configured unit.

    The currency case intentionally differs between axis and tooltip to preserve
    the original behavior: axis ticks show a bare localized number (no symbol),
    while the hover tooltip shows the full currency string.
    """
    if value_format == "currency":
        if for_axis:
            return format_number(value, decimals)
        return format_currency(value, currency_code)
    if value_format == "percent":
        return f"{format_number(value, decimals)}%"
    return format_number(value, decimals)


class _ValueAxis(pg.AxisItem):
    """Left (value) axis that formats ticks with the active locale."""

    def __init__(self, *args, formatter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._formatter = formatter or (lambda v: format_number(v, 0))

    def tickStrings(self, values, scale, spacing):
        return [self._formatter(v) for v in values]


def configure_pyqtgraph_theme() -> None:
    pg.setConfigOption("background", theme.SURFACE)
    pg.setConfigOption("foreground", theme.TEXT_SECONDARY)
    pg.setConfigOption("antialias", True)


def _resolve_color(series_name: str, index: int) -> str:
    lowered = series_name.lower()
    if lowered == "income":
        return theme.INCOME
    if lowered == "expenses":
        return theme.EXPENSE
    if lowered == "net":
        return theme.PRIMARY
    return theme.CHART_CATEGORICAL[index % len(theme.CHART_CATEGORICAL)]


class ChartWidget(QWidget):
    """pyqtgraph-backed line/bar chart. Feed it with set_series()."""

    def __init__(
        self,
        chart_type: str,
        parent=None,
        value_format: str = "currency",
        value_decimals: int = 0,
        currency_code: str = "BRL",
    ):
        super().__init__(parent)
        self._chart_type = chart_type  # "line" | "bar"
        # Value formatting for the left axis + hover tooltip. Defaults preserve
        # the original behavior (BRL currency, 0-decimal ticks) so existing
        # dashboard charts are unaffected; the Market/indicators tab overrides
        # these to render percentages and exchange rates correctly.
        self._value_format = value_format  # "currency" | "number" | "percent"
        self._value_decimals = value_decimals
        self._currency_code = currency_code

        # Hover state: geometry of the drawn marks (in data/view coordinates)
        # so mouse moves can hit-test a bar or a line node and show a tooltip,
        # mirroring PieChartWidget's per-slice hover.
        self._hover_bars: List[tuple] = []   # (name, label, value, x0, x1, y_lo, y_hi)
        self._hover_nodes: List[tuple] = []  # (name, label, value, x, y)
        self._show_series_name = False

        self._plot = pg.PlotWidget(
            axisItems={"left": _ValueAxis(orientation="left", formatter=self._format_axis_value)}
        )
        self._plot.showGrid(x=False, y=True, alpha=0.3)
        self._plot.getAxis("left").setTextPen(theme.TEXT_SECONDARY)
        self._plot.getAxis("bottom").setTextPen(theme.TEXT_SECONDARY)
        self._legend = self._plot.addLegend(offset=(10, 10))

        self._empty_label = QLabel("")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self._empty_label.hide()
        self._empty_label.setSizePolicy(QSizePolicy.Ignored, self._empty_label.sizePolicy().verticalPolicy())

        # pyqtgraph's PlotWidget defaults to a Preferred/Expanding size
        # policy, which (like any policy carrying the Shrink flag) makes
        # Qt's layout engine treat its minimumSizeHint() as a hard floor -
        # setMinimumSize(0, 0) would NOT override that (0 is already the
        # unset default, so it's a no-op; the actual fix is Ignored). Without
        # this, this chart would fight the dashboard grid's fixed row/column
        # sizing (see dashboard_grid_widget.py) the way the old hardcoded
        # setMinimumHeight(160) on PieChartWidget used to.
        self._plot.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)
        layout.addWidget(self._empty_label)

        # Hover a bar / line node -> tooltip with its value (see PieChartWidget).
        self._plot.scene().sigMouseMoved.connect(self._on_scene_mouse_moved)

    def set_value_format(
        self, value_format: str, decimals: int = 0, currency_code: str = "BRL"
    ) -> None:
        """Reconfigure axis/tooltip value formatting (e.g. when the Market tab
        switches between a percentage indicator and an exchange rate)."""
        self._value_format = value_format
        self._value_decimals = decimals
        self._currency_code = currency_code

    def set_empty_state(self, message: str) -> None:
        self._hover_bars = []
        self._hover_nodes = []
        self._plot.hide()
        self._empty_label.setText(message)
        self._empty_label.show()

    def set_series(
        self, labels: List[str], series: Dict[str, List[float]], forecast_count: int = 0,
    ) -> None:
        self._plot.clear()
        self._legend.clear()
        self._hover_bars = []
        self._hover_nodes = []

        if not labels or not series or not any(series.values()):
            self.set_empty_state(t("chart.no_data"))
            return

        self._empty_label.hide()
        self._plot.show()

        x = list(range(len(labels)))
        axis = self._plot.getAxis("bottom")
        # Thin the bottom-axis labels so dense series (e.g. ~120 daily indicator
        # points) don't render as an unreadable smear. All data points and hover
        # nodes are kept; only the tick labels are strided. First and last are
        # always shown. Sparse series (<= max_ticks) are unaffected.
        max_ticks = 12
        step = max(1, len(labels) // max_ticks)
        ticks = [
            (xi, label)
            for i, (xi, label) in enumerate(zip(x, labels))
            if i % step == 0 or i == len(labels) - 1
        ]
        axis.setTicks([ticks])

        names = list(series.keys())
        n_series = len(names)
        self._show_series_name = n_series > 1

        if self._chart_type == "bar":
            group_width = 0.8
            bar_width = group_width / max(n_series, 1)
            for idx, name in enumerate(names):
                values = series[name]
                color = _resolve_color(name, idx)
                offsets = [xi - group_width / 2 + bar_width * (idx + 0.5) for xi in x]
                item = pg.BarGraphItem(x=offsets, height=values, width=bar_width * 0.9, brush=color, pen=color)
                self._plot.addItem(item)
                self._legend.addItem(item, name)
                half = bar_width * 0.9 / 2
                for offset, label, value in zip(offsets, labels, values):
                    y_lo, y_hi = (0, value) if value >= 0 else (value, 0)
                    self._hover_bars.append(
                        (name, label, value, offset - half, offset + half, y_lo, y_hi)
                    )
        else:
            # split = index of the first forecast point; the historical part is
            # drawn solid and the forecast tail dashed, overlapping by one point
            # (split - 1) so the two segments join continuously.
            split = len(labels) - forecast_count if forecast_count > 0 else len(labels)
            for idx, name in enumerate(names):
                values = series[name]
                color = _resolve_color(name, idx)
                for xi, label, value in zip(x, labels, values):
                    self._hover_nodes.append((name, label, value, xi, value))
                if 0 < split < len(values):
                    solid = pg.PlotDataItem(
                        x[:split], values[:split],
                        pen=pg.mkPen(color=color, width=2), symbol="o", symbolSize=6,
                        symbolBrush=color, symbolPen=color,
                    )
                    self._plot.addItem(solid)
                    self._legend.addItem(solid, name)
                    forecast = pg.PlotDataItem(
                        x[split - 1:], values[split - 1:],
                        pen=pg.mkPen(color=color, width=2, style=Qt.DashLine),
                        symbol="o", symbolSize=6, symbolBrush=color, symbolPen=color,
                    )
                    self._plot.addItem(forecast)  # no legend entry - avoids a duplicate row
                else:
                    curve = pg.PlotDataItem(
                        x, values, pen=pg.mkPen(color=color, width=2), symbol="o", symbolSize=6,
                        symbolBrush=color, symbolPen=color,
                    )
                    self._plot.addItem(curve)
                    self._legend.addItem(curve, name)

        self._legend.setVisible(n_series > 1)

    def _format_axis_value(self, value: float) -> str:
        return _format_value(
            value, self._value_format, self._value_decimals, self._currency_code,
            for_axis=True,
        )

    def _tooltip_text(self, name: str, label: str, value: float) -> str:
        body = "{}: {}".format(
            label,
            _format_value(value, self._value_format, self._value_decimals, self._currency_code),
        )
        return f"{name} — {body}" if self._show_series_name else body

    def _on_scene_mouse_moved(self, scene_pos) -> None:
        if not self._hover_bars and not self._hover_nodes:
            return
        plot_item = self._plot.getPlotItem()
        if not plot_item.sceneBoundingRect().contains(scene_pos):
            QToolTip.hideText()
            return

        view_box = plot_item.getViewBox()
        view_pt = view_box.mapSceneToView(scene_pos)
        hit = None

        if self._chart_type == "bar":
            vx, vy = view_pt.x(), view_pt.y()
            for name, label, value, x0, x1, y_lo, y_hi in self._hover_bars:
                if x0 <= vx <= x1 and y_lo <= vy <= y_hi:
                    hit = (name, label, value)
                    break
        else:
            # Nearest node within a small pixel radius, measured in scene
            # (pixel) space so the threshold is consistent regardless of the
            # axis scales.
            best_dist = None
            for name, label, value, x, y in self._hover_nodes:
                node_scene = view_box.mapViewToScene(QPointF(x, y))
                dist = math.hypot(node_scene.x() - scene_pos.x(), node_scene.y() - scene_pos.y())
                if dist <= 15 and (best_dist is None or dist < best_dist):
                    best_dist = dist
                    hit = (name, label, value)

        if hit is None:
            QToolTip.hideText()
            return
        QToolTip.showText(QCursor.pos(), self._tooltip_text(*hit), self._plot)


class PieChartWidget(QWidget):
    """Custom-painted pie chart - pyqtgraph has no native pie primitive."""

    # Emitted when a slice is clicked: (index into the fed labels, label).
    # The index matches the order passed to set_series (entries with value <= 0
    # are dropped, so feed only positive values to keep indices aligned).
    slice_clicked = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Ignored (not just setMinimumSize(0, 0), which is a no-op - see
        # ChartWidget above) so this never forces whichever row/column it
        # lands in to grow past the dashboard grid's fixed unit size (see
        # dashboard_grid_widget.py) the way the old hardcoded
        # setMinimumHeight(160) used to.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMouseTracking(True)  # hover a slice -> tooltip with its value
        self._entries: List[tuple] = []
        self._empty_message: Optional[str] = t("chart.no_data")

    def set_empty_state(self, message: str) -> None:
        self._entries = []
        self._empty_message = message
        self.update()

    def set_series(self, labels: List[str], series: Dict[str, List[float]]) -> None:
        if not labels or not series:
            self.set_empty_state(t("chart.no_data"))
            return

        # Pie charts always show a single metric (enforced by the builder dialog).
        values = next(iter(series.values()))
        total = sum(v for v in values if v > 0)
        if total <= 0:
            self.set_empty_state(t("chart.no_data"))
            return

        self._empty_message = None
        self._entries = [
            (label, value, theme.CHART_CATEGORICAL[idx % len(theme.CHART_CATEGORICAL)])
            for idx, (label, value) in enumerate(zip(labels, values))
            if value > 0
        ]
        self.update()

    def _pie_rect(self) -> Optional[QRectF]:
        """Geometry of the drawn pie, or None when there is nothing to draw.

        Shared by paintEvent and the hover hit-test so the two never drift.
        """
        if self._empty_message or not self._entries:
            return None
        rect = self.rect()
        legend_width = 150
        pie_size = max(min(rect.width() - legend_width, rect.height()) - 20, 20)
        return QRectF(10, (rect.height() - pie_size) / 2, pie_size, pie_size)

    def _slice_at(self, pos) -> Optional[int]:
        """Index of the pie slice under `pos`, or None if outside the pie."""
        pie_rect = self._pie_rect()
        if pie_rect is None:
            return None
        center = pie_rect.center()
        radius = pie_rect.width() / 2
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        if math.hypot(dx, dy) > radius:
            return None
        total = sum(value for _, value, _ in self._entries)
        if total <= 0:
            return None
        # Slices are painted clockwise from 12 o'clock (see paintEvent). Convert
        # the cursor to a clockwise angle from the top, then walk the slices.
        theta = (90 - math.degrees(math.atan2(-dy, dx))) % 360
        acc = 0.0
        for idx, (_, value, _) in enumerate(self._entries):
            acc += value / total * 360
            if theta < acc:
                return idx
        return len(self._entries) - 1

    def mouseMoveEvent(self, event):
        idx = self._slice_at(event.position().toPoint()) if self._entries else None
        if idx is None:
            QToolTip.hideText()
            self.unsetCursor()
        else:
            label, value, _ = self._entries[idx]
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"{label}: {format_currency(value, 'BRL')}", self)
            self.setCursor(Qt.PointingHandCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._entries:
            idx = self._slice_at(event.position().toPoint())
            if idx is not None:
                label, _value, _color = self._entries[idx]
                self.slice_clicked.emit(idx, label)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        if self._empty_message:
            painter.setPen(QColor(theme.TEXT_SECONDARY))
            painter.drawText(rect, Qt.AlignCenter, self._empty_message)
            return

        pie_rect = self._pie_rect()
        if pie_rect is None:
            return

        total = sum(value for _, value, _ in self._entries)
        start_angle = 90 * 16
        for _, value, color in self._entries:
            span = int(round(360 * 16 * (value / total)))
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor(theme.SURFACE), 2))
            painter.drawPie(pie_rect, start_angle, -span)
            start_angle -= span

        legend_x = pie_rect.right() + 20
        legend_y = pie_rect.top()
        font = QFont(painter.font().family(), 9)
        painter.setFont(font)
        for label, value, color in self._entries:
            if legend_y > rect.height() - 20:
                break  # avoid overflowing the widget with too many slices
            painter.setBrush(QColor(color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(legend_x), int(legend_y) + 2, 10, 10)
            painter.setPen(QColor(theme.TEXT_PRIMARY))
            pct = value / total * 100
            painter.drawText(int(legend_x) + 16, int(legend_y) + 11, f"{label} ({format_number(pct, 0)}%)")
            legend_y += 18
