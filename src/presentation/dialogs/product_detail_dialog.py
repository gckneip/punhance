from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from src.presentation import theme
from src.presentation.i18n import format_currency, format_date, t


class ProductDetailDialog(QDialog):
    def __init__(self, parent, product, events, average_price=None):
        super().__init__(parent)
        self.setWindowTitle(t("product_detail.title", name=product.name))
        self.setModal(True)
        self.resize(560, 420)

        layout = QVBoxLayout(self)

        if not events:
            layout.addWidget(QLabel(t("product_detail.no_events")))
        else:
            table = QTableWidget(len(events), 5)
            table.setHorizontalHeaderLabels([
                t("common.date"),
                t("common.description"),
                t("product_detail.quantity"),
                t("product_detail.unit_price"),
                t("product_detail.total"),
            ])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setAlternatingRowColors(True)
            for row, event in enumerate(events):
                table.setItem(row, 0, QTableWidgetItem(format_date(event.event_date) if event.event_date else ""))
                table.setItem(row, 1, QTableWidgetItem(event.description or ""))
                table.setItem(row, 2, QTableWidgetItem(f"{event.quantity:g} {event.unit}"))

                price_item = QTableWidgetItem(format_currency(event.unit_price))
                if average_price is not None:
                    if event.unit_price < average_price:
                        price_item.setForeground(QColor(theme.INCOME))
                    elif event.unit_price > average_price:
                        price_item.setForeground(QColor(theme.EXPENSE))
                table.setItem(row, 3, price_item)

                table.setItem(row, 4, QTableWidgetItem(format_currency(event.total_price)))
            table.resizeColumnsToContents()
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
