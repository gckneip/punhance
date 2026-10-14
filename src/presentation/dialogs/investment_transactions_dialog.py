from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.presentation import icons
from src.presentation.i18n import format_currency, format_date, t
from src.presentation.labels import investment_txn_label
from src.presentation.dialogs.investment_transaction_dialog import (
    InvestmentTransactionDialog,
)
from src.application.dto.investment_transaction_dto import (
    CreateInvestmentTransactionDTO,
)


class InvestmentTransactionsDialog(QDialog):
    """Manage the transaction history of a single investment holding."""

    def __init__(self, parent, investment, investment_use_cases):
        super().__init__(parent)
        self._investment = investment
        self._use_cases = investment_use_cases
        self._currency = investment.currency

        self.setWindowTitle(t("investment_transactions.title", name=investment.name))
        self.setModal(True)
        self.resize(640, 460)

        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(t("investment_transactions.add"))
        add_btn.setIcon(icons.icon("fa6s.circle-plus"))
        add_btn.clicked.connect(self._add_transaction)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            t("common.date"),
            t("common.type"),
            t("investment_transaction_dialog.quantity"),
            t("investment_transaction_dialog.unit_price"),
            t("investment_transaction_dialog.fees"),
            t("investment_transaction_dialog.total"),
            t("common.actions"),
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self):
        transactions = self._use_cases.list_transactions(self._investment.id)
        self._table.setRowCount(len(transactions))
        for i, txn in enumerate(transactions):
            self._table.setItem(i, 0, QTableWidgetItem(format_date(txn.date) if txn.date else ""))
            self._table.setItem(i, 1, QTableWidgetItem(investment_txn_label(txn.txn_type)))
            qty = f"{txn.quantity:g}" if txn.quantity else ""
            self._table.setItem(i, 2, QTableWidgetItem(qty))
            self._table.setItem(i, 3, QTableWidgetItem(
                format_currency(txn.unit_price, self._currency) if txn.unit_price else ""))
            self._table.setItem(i, 4, QTableWidgetItem(
                format_currency(txn.fees, self._currency) if txn.fees else ""))
            self._table.setItem(i, 5, QTableWidgetItem(format_currency(txn.total, self._currency)))
            self._table.setCellWidget(i, 6, self._make_actions(txn))

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def _make_actions(self, txn):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(4)
        for label, icon_name, handler in (
            (t("common.edit"), "fa6s.pen", lambda: self._edit_transaction(txn)),
            (t("common.delete"), "fa6s.trash", lambda: self._delete_transaction(txn)),
        ):
            btn = QPushButton()
            btn.setIcon(icons.icon(icon_name))
            btn.setIconSize(QSize(16, 16))
            btn.setToolTip(label)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(handler)
            row.addWidget(btn)
        row.addStretch()
        return widget

    def _add_transaction(self):
        dialog = InvestmentTransactionDialog(self, currency=self._currency)
        if dialog.exec():
            data = dialog.get_data()
            self._use_cases.add_transaction(CreateInvestmentTransactionDTO(
                investment_id=self._investment.id,
                txn_type=data["txn_type"],
                date=data["date"],
                quantity=data["quantity"],
                unit_price=data["unit_price"],
                fees=data["fees"],
                total=data["total"],
                notes=data["notes"],
            ))
            self._refresh()

    def _edit_transaction(self, txn):
        dialog = InvestmentTransactionDialog(self, transaction=txn, currency=self._currency)
        if dialog.exec():
            data = dialog.get_data()
            self._use_cases.update_transaction(txn.id, CreateInvestmentTransactionDTO(
                investment_id=self._investment.id,
                txn_type=data["txn_type"],
                date=data["date"],
                quantity=data["quantity"],
                unit_price=data["unit_price"],
                fees=data["fees"],
                total=data["total"],
                notes=data["notes"],
            ))
            self._refresh()

    def _delete_transaction(self, txn):
        reply = QMessageBox.question(
            self,
            t("investment_transactions.delete_title"),
            t("investment_transactions.delete_body"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._use_cases.delete_transaction(txn.id)
        self._refresh()
