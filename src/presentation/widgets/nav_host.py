from PySide6.QtCore import QEvent, QSize, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
    QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)

from src.presentation import icons, theme

NAV_COLLAPSED_WIDTH = 64
_MIN_EXPANDED_WIDTH = 160
_EXPANDED_WIDTH_PADDING = 56  # icon-text gap + item padding/margins + safety buffer

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
    QStackedWidget on the right.

    Two independent axes:
    - collapsed/expanded: the hamburger button toggles between an icon-only
      rail and the full icon+label list. The expanded width auto-fits
      whatever the longest label needs (via _update_expanded_width), so
      labels never clip regardless of font size.
    - fixed/drawer mode (the pin button toggles this, live, no restart):
      "fixed" is the classic docked behavior above - expanding pushes the
      page content over. "drawer" keeps a slim rail permanently docked and
      instead pops the expanded list out as a floating overlay on top of
      the content (like VS Code's Source Control panel), closing again on
      an outside click or on picking a page.
    """

    mode_changed = Signal(str)

    def __init__(self, parent=None, mode="fixed"):
        super().__init__(parent)
        self._mode = mode if mode in ("fixed", "drawer") else "fixed"
        self._collapsed = False
        self._drawer_open = False
        self._rail_placeholder = None
        self._filter_installed = False
        self._labels = []
        self._expanded_width = _MIN_EXPANDED_WIDTH

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._nav_column = QWidget()
        nav_layout = QVBoxLayout(self._nav_column)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(6, 6, 6, 6)
        toggle_row.setSpacing(4)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setIcon(icons.icon("fa6s.bars"))
        self._toggle_btn.setToolTip("Collapse/expand the sidebar")
        self._toggle_btn.setFixedWidth(26)
        self._toggle_btn.clicked.connect(self._on_hamburger_clicked)
        toggle_row.addWidget(self._toggle_btn)

        self._mode_btn = QPushButton()
        self._mode_btn.setFixedWidth(26)
        self._mode_btn.clicked.connect(self._toggle_mode)
        toggle_row.addWidget(self._mode_btn)

        toggle_row.addStretch()
        nav_layout.addLayout(toggle_row)

        self._nav_list = QListWidget()
        self._nav_list.setObjectName("sidebarNav")
        self._nav_list.setIconSize(QSize(20, 20))
        self._nav_list.currentRowChanged.connect(self._on_row_changed)
        nav_layout.addWidget(self._nav_list)

        self._nav_column.setFixedWidth(
            NAV_COLLAPSED_WIDTH if self._mode == "drawer" else self._expanded_width
        )
        outer.addWidget(self._nav_column)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack, stretch=1)

        self._update_mode_button()

    def addTab(self, widget, icon, label):
        return self.insertTab(self._stack.count(), widget, icon, label)

    def insertTab(self, index, widget, icon, label):
        actual_index = self._stack.insertWidget(index, widget)
        self._labels.insert(actual_index, label)
        expanded_now = self._is_showing_labels()
        item = QListWidgetItem(icon, label if expanded_now else "")
        if not expanded_now:
            item.setToolTip(label)
        self._nav_list.insertItem(actual_index, item)
        self._update_expanded_width(label)
        return actual_index

    def setCurrentIndex(self, index):
        self._nav_list.setCurrentRow(index)
        self._stack.setCurrentIndex(index)

    def setCurrentWidget(self, widget):
        index = self._stack.indexOf(widget)
        if index >= 0:
            self.setCurrentIndex(index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._mode == "drawer" and self._drawer_open:
            self._nav_column.setGeometry(0, 0, self._expanded_width, self.height())

    def eventFilter(self, obj, event):
        if self._drawer_open and event.type() == QEvent.MouseButtonPress:
            local_pos = self._nav_column.mapFromGlobal(event.globalPosition().toPoint())
            if not self._nav_column.rect().contains(local_pos):
                self._close_drawer()
        return super().eventFilter(obj, event)

    def _is_showing_labels(self) -> bool:
        if self._mode == "fixed":
            return not self._collapsed
        return self._drawer_open

    def _on_row_changed(self, row):
        if row >= 0:
            self._stack.setCurrentIndex(row)
        if self._mode == "drawer" and self._drawer_open:
            self._close_drawer()

    def _on_hamburger_clicked(self):
        if self._mode == "fixed":
            self._toggle_collapsed()
        elif self._drawer_open:
            self._close_drawer()
        else:
            self._open_drawer()

    def _toggle_collapsed(self):
        self._collapsed = not self._collapsed
        self._nav_column.setFixedWidth(NAV_COLLAPSED_WIDTH if self._collapsed else self._expanded_width)
        self._set_items_expanded(not self._collapsed)

    def _set_items_expanded(self, expanded: bool):
        for i in range(self._nav_list.count()):
            item = self._nav_list.item(i)
            item.setText(self._labels[i] if expanded else "")
            item.setToolTip("" if expanded else self._labels[i])

    def _open_drawer(self):
        self._drawer_open = True
        self._set_items_expanded(True)

        outer_layout = self.layout()
        idx = outer_layout.indexOf(self._nav_column)
        if idx != -1:
            outer_layout.removeWidget(self._nav_column)
            self._rail_placeholder = QWidget()
            self._rail_placeholder.setFixedWidth(NAV_COLLAPSED_WIDTH)
            outer_layout.insertWidget(idx, self._rail_placeholder)

        # setFixedWidth() (used for the docked rail state) locks both min
        # and max width - clear that lock first, or setGeometry() below
        # would get silently clamped back down to the old fixed width.
        self._nav_column.setMinimumWidth(0)
        self._nav_column.setMaximumWidth(16_777_215)
        self._nav_column.setParent(self)
        self._nav_column.setGeometry(0, 0, self._expanded_width, self.height())
        self._nav_column.raise_()
        self._nav_column.show()

        if not self._filter_installed:
            QApplication.instance().installEventFilter(self)
            self._filter_installed = True

    def _close_drawer(self):
        self._drawer_open = False
        self._set_items_expanded(False)

        if self._filter_installed:
            QApplication.instance().removeEventFilter(self)
            self._filter_installed = False

        outer_layout = self.layout()
        if self._rail_placeholder is not None:
            idx = outer_layout.indexOf(self._rail_placeholder)
            outer_layout.removeWidget(self._rail_placeholder)
            self._rail_placeholder.deleteLater()
            self._rail_placeholder = None
            outer_layout.insertWidget(idx, self._nav_column)
        self._nav_column.setFixedWidth(NAV_COLLAPSED_WIDTH)

    def _toggle_mode(self):
        if self._mode == "fixed":
            if not self._collapsed:
                self._toggle_collapsed()
            self._mode = "drawer"
        else:
            if self._drawer_open:
                self._close_drawer()
            self._mode = "fixed"
            self._nav_column.setFixedWidth(self._expanded_width)
            self._set_items_expanded(True)
            self._collapsed = False
        self._update_mode_button()
        self.mode_changed.emit(self._mode)

    def _update_mode_button(self):
        pinned = self._mode == "fixed"
        self._mode_btn.setIcon(icons.icon("fa6s.thumbtack", color=theme.PRIMARY if pinned else theme.TEXT_SECONDARY))
        self._mode_btn.setToolTip(
            "Pinned: sidebar always docked - click to make it an overlay drawer"
            if pinned else
            "Drawer: sidebar overlays the page on demand - click to pin it docked"
        )

    def _update_expanded_width(self, label):
        # Query the app's current base font size directly rather than
        # self._nav_list.fontMetrics(): a freshly-constructed widget hasn't
        # been polished with the app stylesheet yet at this point (that only
        # happens on first paint), so its fontMetrics() would still reflect
        # Qt's small default font and under-measure the real rendered size.
        font = QFont(self._nav_list.font())
        font.setPixelSize(theme.BASE_FONT_SIZE)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(label)
        icon_width = self._nav_list.iconSize().width()
        needed = icon_width + text_width + _EXPANDED_WIDTH_PADDING
        if needed <= self._expanded_width:
            return
        self._expanded_width = needed
        if self._mode == "fixed" and not self._collapsed:
            self._nav_column.setFixedWidth(self._expanded_width)
        elif self._mode == "drawer" and self._drawer_open:
            self._nav_column.setGeometry(0, 0, self._expanded_width, self.height())
