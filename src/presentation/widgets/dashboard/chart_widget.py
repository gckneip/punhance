from typing import Dict, List, Optional

import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.presentation import theme


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

    def __init__(self, chart_type: str, parent=None):
        super().__init__(parent)
        self._chart_type = chart_type  # "line" | "bar"

        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=False, y=True, alpha=0.3)
        self._plot.getAxis("left").setTextPen(theme.TEXT_SECONDARY)
        self._plot.getAxis("bottom").setTextPen(theme.TEXT_SECONDARY)
        self._legend = self._plot.addLegend(offset=(10, 10))

        self._empty_label = QLabel("")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self._empty_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)
        layout.addWidget(self._empty_label)

    def set_empty_state(self, message: str) -> None:
        self._plot.hide()
        self._empty_label.setText(message)
        self._empty_label.show()

    def set_series(self, labels: List[str], series: Dict[str, List[float]]) -> None:
        self._plot.clear()
        self._legend.clear()

        if not labels or not series or not any(series.values()):
            self.set_empty_state("No data for this range.")
            return

        self._empty_label.hide()
        self._plot.show()

        x = list(range(len(labels)))
        axis = self._plot.getAxis("bottom")
        axis.setTicks([[(xi, label) for xi, label in zip(x, labels)]])

        names = list(series.keys())
        n_series = len(names)

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
        else:
            for idx, name in enumerate(names):
                values = series[name]
                color = _resolve_color(name, idx)
                pen = pg.mkPen(color=color, width=2)
                curve = pg.PlotDataItem(
                    x, values, pen=pen, symbol="o", symbolSize=6,
                    symbolBrush=color, symbolPen=color,
                )
                self._plot.addItem(curve)
                self._legend.addItem(curve, name)

        self._legend.setVisible(n_series > 1)


class PieChartWidget(QWidget):
    """Custom-painted pie chart - pyqtgraph has no native pie primitive."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self._entries: List[tuple] = []
        self._empty_message: Optional[str] = "No data for this range."

    def set_empty_state(self, message: str) -> None:
        self._entries = []
        self._empty_message = message
        self.update()

    def set_series(self, labels: List[str], series: Dict[str, List[float]]) -> None:
        if not labels or not series:
            self.set_empty_state("No data for this range.")
            return

        # Pie charts always show a single metric (enforced by the builder dialog).
        values = next(iter(series.values()))
        total = sum(v for v in values if v > 0)
        if total <= 0:
            self.set_empty_state("No data for this range.")
            return

        self._empty_message = None
        self._entries = [
            (label, value, theme.CHART_CATEGORICAL[idx % len(theme.CHART_CATEGORICAL)])
            for idx, (label, value) in enumerate(zip(labels, values))
            if value > 0
        ]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        if self._empty_message:
            painter.setPen(QColor(theme.TEXT_SECONDARY))
            painter.drawText(rect, Qt.AlignCenter, self._empty_message)
            return

        legend_width = 150
        pie_size = max(min(rect.width() - legend_width, rect.height()) - 20, 20)
        pie_rect = QRectF(10, (rect.height() - pie_size) / 2, pie_size, pie_size)

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
            painter.drawText(int(legend_x) + 16, int(legend_y) + 11, f"{label} ({pct:.0f}%)")
            legend_y += 18
