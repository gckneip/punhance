from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from src.presentation import theme
from src.presentation.i18n import format_currency, format_date, t
from src.presentation.labels import event_type_label


class CategoryEventsDialog(QDialog):
    """Drill-down modal listing the individual events of a single category,
    opened from the category-breakdown pie chart or table."""

    def __init__(self, parent, category_name, rows):
        super().__init__(parent)
        self.setWindowTitle(t("category_events.title", name=category_name))
        self.setModal(True)
        self.resize(560, 420)

        layout = QVBoxLayout(self)

        if not rows:
            layout.addWidget(QLabel(t("category_events.no_events")))
        else:
            total = sum((-r.amount if r.is_income else r.amount) for r in rows)
            summary = QLabel(t(
                "category_events.summary",
                count=len(rows),
                total=format_currency(abs(total), rows[0].currency),
            ))
            layout.addWidget(summary)

            table = QTableWidget(len(rows), 4)
            table.setHorizontalHeaderLabels([
                t("common.date"),
                t("common.description"),
                t("common.type"),
                t("common.amount"),
            ])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableWidget.SelectRows)

            for row, entry in enumerate(rows):
                table.setItem(row, 0, QTableWidgetItem(
                    format_date(entry.event_date) if entry.event_date else ""))
                table.setItem(row, 1, QTableWidgetItem(entry.description or ""))
                table.setItem(row, 2, QTableWidgetItem(event_type_label(entry.event_type)))

                amount_item = QTableWidgetItem(format_currency(entry.amount, entry.currency))
                amount_item.setForeground(
                    QColor(theme.INCOME if entry.is_income else theme.EXPENSE))
                table.setItem(row, 3, amount_item)

            table.resizeColumnsToContents()
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
