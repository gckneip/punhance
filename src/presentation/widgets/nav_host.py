from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget,
)

from src.presentation import icons

NAV_EXPANDED_WIDTH = 190
NAV_COLLAPSED_WIDTH = 52

# Both classes below implement the same small interface so MainWindow can
# swap between them at construction time based on the persisted navigation
# style, with every other call site (addTab/insertTab/setCurrentIndex/
# setCurrentWidget) left untouched:
#   addTab(widget, icon, label) -> int
#   insertTab(index, widget, icon, label) -> int
#   setCurrentIndex(index) -> None
#   setCurrentWidget(widget) -> None
# No shared ABC base - mixing ABC and QWidget metaclasses is a footgun, and
# duck typing is enough for this small a surface.


class TabNavHost(QWidget):
    """Current/default navigation: a QTabWidget across the top."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

    def addTab(self, widget, icon, label):
        return self._tabs.addTab(widget, icon, label)

    def insertTab(self, index, widget, icon, label):
        return self._tabs.insertTab(index, widget, icon, label)

    def setCurrentIndex(self, index):
        self._tabs.setCurrentIndex(index)

    def setCurrentWidget(self, widget):
        self._tabs.setCurrentWidget(widget)


class SidebarNavHost(QWidget):
    """Alternate navigation: a collapsible icon+label list on the left, a
    QStackedWidget on the right. The toggle button collapses the list down
    to an icon-only rail (labels move to tooltips) rather than hiding it
    outright."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self._labels = []

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._nav_column = QWidget()
        nav_layout = QVBoxLayout(self._nav_column)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(6, 6, 6, 6)
        self._toggle_btn = QPushButton()
        self._toggle_btn.setIcon(icons.icon("fa6s.bars"))
        self._toggle_btn.setToolTip("Collapse/expand the sidebar")
        self._toggle_btn.setFixedWidth(32)
        self._toggle_btn.clicked.connect(self._toggle_collapsed)
        toggle_row.addWidget(self._toggle_btn)
        toggle_row.addStretch()
        nav_layout.addLayout(toggle_row)

        self._nav_list = QListWidget()
        self._nav_list.setObjectName("sidebarNav")
        self._nav_list.setIconSize(QSize(20, 20))
        self._nav_list.currentRowChanged.connect(self._on_row_changed)
        nav_layout.addWidget(self._nav_list)

        self._nav_column.setFixedWidth(NAV_EXPANDED_WIDTH)
        outer.addWidget(self._nav_column)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack, stretch=1)

    def addTab(self, widget, icon, label):
        return self.insertTab(self._stack.count(), widget, icon, label)

    def insertTab(self, index, widget, icon, label):
        actual_index = self._stack.insertWidget(index, widget)
        self._labels.insert(actual_index, label)
        item = QListWidgetItem(icon, "" if self._collapsed else label)
        if self._collapsed:
            item.setToolTip(label)
        self._nav_list.insertItem(actual_index, item)
        return actual_index

    def setCurrentIndex(self, index):
        self._nav_list.setCurrentRow(index)
        self._stack.setCurrentIndex(index)

    def setCurrentWidget(self, widget):
        index = self._stack.indexOf(widget)
        if index >= 0:
            self.setCurrentIndex(index)

    def _on_row_changed(self, row):
        if row >= 0:
            self._stack.setCurrentIndex(row)

    def _toggle_collapsed(self):
        self._collapsed = not self._collapsed
        self._nav_column.setFixedWidth(NAV_COLLAPSED_WIDTH if self._collapsed else NAV_EXPANDED_WIDTH)
        for i in range(self._nav_list.count()):
            item = self._nav_list.item(i)
            item.setText("" if self._collapsed else self._labels[i])
            item.setToolTip(self._labels[i] if self._collapsed else "")
