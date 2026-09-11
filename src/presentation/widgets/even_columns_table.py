from PySide6.QtWidgets import QTableWidget


class EvenColumnsTableWidget(QTableWidget):
    """A QTableWidget that fills its full available width every time it's
    resized, spreading the leftover space evenly across every column on top
    of each column's natural (content-driven) width - instead of the default
    "stretch last section" behavior, which dumps all the extra space into
    just the last column and leaves the rest looking cramped."""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._distribute_columns()

    def resizeColumnsToContents(self):
        # Overridden (not just relying on resizeEvent) because every call
        # site calls this right after repopulating rows to size columns to
        # the new content - the base QTableWidget implementation shrinks
        # each column to its tight natural width with no regard for leftover
        # viewport space, undoing the even-fill distribution below until the
        # next real widget resize. Redirecting here keeps every existing
        # call site's intent ("fit the new content") while preserving the
        # full-width fill.
        self._distribute_columns()

    def _distribute_columns(self):
        column_count = self.columnCount()
        if column_count == 0:
            return

        header = self.horizontalHeader()
        # sizeHintForColumn only looks at cell contents, so a column whose
        # header label (e.g. "Counterparty") is longer than every value in
        # it would get sized too narrow and clip the header text - take the
        # header's own size hint into account too, and use whichever is wider.
        natural_widths = [
            max(self.sizeHintForColumn(i), header.sectionSizeHint(i), 1)
            for i in range(column_count)
        ]
        available = self.viewport().width()
        extra = max(0, available - sum(natural_widths))
        bonus, remainder = divmod(extra, column_count)

        for i in range(column_count):
            width = natural_widths[i] + bonus + (1 if i < remainder else 0)
            header.resizeSection(i, width)
