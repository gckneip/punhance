from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from src.presentation import theme


class ProductDetailDialog(QDialog):
    def __init__(self, parent, product, events, average_price=None):
        super().__init__(parent)
        self.setWindowTitle(f"Recent Events - {product.name}")
        self.setModal(True)
        self.resize(560, 420)

        layout = QVBoxLayout(self)

        if not events:
            layout.addWidget(QLabel("No purchase events for this product yet."))
        else:
            table = QTableWidget(len(events), 5)
            table.setHorizontalHeaderLabels(["Date", "Description", "Quantity", "Unit Price", "Total"])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setAlternatingRowColors(True)
            for row, event in enumerate(events):
                table.setItem(row, 0, QTableWidgetItem(event.event_date.isoformat() if event.event_date else ""))
                table.setItem(row, 1, QTableWidgetItem(event.description or ""))
                table.setItem(row, 2, QTableWidgetItem(f"{event.quantity:g} {event.unit}"))

                price_item = QTableWidgetItem(f"R$ {event.unit_price:.2f}")
                if average_price is not None:
                    if event.unit_price < average_price:
                        price_item.setForeground(QColor(theme.INCOME))
                    elif event.unit_price > average_price:
                        price_item.setForeground(QColor(theme.EXPENSE))
                table.setItem(row, 3, price_item)

                table.setItem(row, 4, QTableWidgetItem(f"R$ {event.total_price:.2f}"))
            table.resizeColumnsToContents()
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
