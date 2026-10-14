from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.presentation import icons, theme
from src.presentation.i18n import format_currency, format_date, format_number, t
from src.presentation.labels import asset_type_label
from src.presentation.widgets.dashboard.investment_widget_renderer import format_yield
from src.presentation.dialogs.investment_dialog import InvestmentDialog
from src.presentation.dialogs.investment_transactions_dialog import InvestmentTransactionsDialog
from src.presentation.dialogs.investment_schedules_dialog import InvestmentSchedulesDialog
from src.application.dto.investment_dto import CreateInvestmentDTO
from src.domain.entities.investment import AssetType


class HoldingsPanel(QWidget):
    """Manage investment holdings (add/edit/delete/transactions/update-price).

    The reusable body behind both the "Carteira" tab and (historically) the
    Holdings Manager dialog: a holdings table with per-row actions. Emits
    ``changed`` after any mutation so the host can record a portfolio snapshot
    and refresh the analytics dashboard.
    """

    changed = Signal()

    def __init__(self, investment_use_cases, account_use_cases, parent=None):
        super().__init__(parent)
        self._use_cases = investment_use_cases
        self._account_use_cases = account_use_cases

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(t("mainwindow.btn.add_investment"))
        add_btn.setIcon(icons.icon("fa6s.circle-plus"))
        add_btn.clicked.connect(self._add_investment)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            t("common.name"),
            t("mainwindow.table.investments.header.type"),
            t("mainwindow.table.investments.header.quantity"),
            t("mainwindow.table.investments.header.avg_price"),
            t("mainwindow.table.investments.header.current_price"),
            t("mainwindow.table.investments.header.market_value"),
            t("mainwindow.table.investments.header.gain"),
            t("mainwindow.table.investments.header.yield"),
            t("mainwindow.table.investments.header.maturity"),
            t("common.actions"),
        ])
        self._table.setObjectName("mainTabTable")
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self.refresh()

    def refresh(self):
        # Savings boxes (Caixinha/Cofrinho) live in their own "Caixinhas" tab with
        # balance/goal columns; this portfolio shows only quantity-priced assets.
        investments = [
            inv for inv in self._use_cases.list_investments()
            if inv.asset_type != AssetType.SAVINGS_BOX
        ]
        self._table.setRowCount(len(investments))
        for i, inv in enumerate(investments):
            self._table.setItem(i, 0, QTableWidgetItem(inv.name))
            self._table.setItem(i, 1, QTableWidgetItem(asset_type_label(inv.asset_type)))
            self._table.setItem(i, 2, QTableWidgetItem(f"{inv.quantity:g}" if inv.quantity else ""))
            self._table.setItem(i, 3, QTableWidgetItem(
                format_currency(inv.avg_unit_price, inv.currency) if inv.avg_unit_price else ""))
            self._table.setItem(i, 4, QTableWidgetItem(format_currency(inv.current_price, inv.currency)))
            self._table.setItem(i, 5, QTableWidgetItem(format_currency(inv.market_value, inv.currency)))
            gain_item = QTableWidgetItem(
                f"{format_currency(inv.total_return, inv.currency)} ({format_number(inv.return_pct, 1)}%)"
            )
            if inv.total_return > 0:
                gain_item.setForeground(QColor(theme.INCOME))
            elif inv.total_return < 0:
                gain_item.setForeground(QColor(theme.EXPENSE))
            self._table.setItem(i, 6, gain_item)
            self._table.setItem(i, 7, QTableWidgetItem(format_yield(inv.yield_rate, inv.yield_index)))
            self._table.setItem(i, 8, QTableWidgetItem(
                format_date(inv.maturity_date) if inv.maturity_date else ""))
            self._table.setCellWidget(i, 9, self._make_actions(inv.id))
        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _make_actions(self, investment_id):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(4)
        for label, icon_name, handler in (
            (t("investments.action.transactions"), "fa6s.list",
             lambda: self._open_transactions(investment_id)),
            (t("investments.action.schedule"), "fa6s.calendar-plus",
             lambda: self._open_schedules(investment_id)),
            (t("investments.action.update_price"), "fa6s.money-bill-trend-up",
             lambda: self._update_price(investment_id)),
            (t("common.edit"), "fa6s.pen", lambda: self._edit_investment(investment_id)),
            (t("common.delete"), "fa6s.trash", lambda: self._delete_investment(investment_id)),
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

    def _dto_from_dialog(self, data):
        return CreateInvestmentDTO(
            name=data["name"], asset_type=data["asset_type"], currency=data["currency"],
            ticker=data["ticker"], account_id=data["account_id"],
            current_price=data["current_price"],
            goal_amount=data.get("goal_amount"), goal_date=data.get("goal_date"),
            yield_rate=data.get("yield_rate"), yield_index=data.get("yield_index", "prefixed"),
            monthly_contribution=data.get("monthly_contribution"),
            maturity_date=data.get("maturity_date"),
            notes=data["notes"], is_active=data["is_active"],
        )

    def _add_investment(self):
        accounts = self._account_use_cases.list_accounts()
        dialog = InvestmentDialog(self, accounts=accounts)
        if dialog.exec():
            self._use_cases.create_investment(self._dto_from_dialog(dialog.get_data()))
            self._on_changed()

    def _edit_investment(self, investment_id):
        investment = self._use_cases.get_investment(investment_id)
        if investment is None:
            return
        accounts = self._account_use_cases.list_accounts()
        dialog = InvestmentDialog(self, investment=investment, accounts=accounts)
        if dialog.exec():
            self._use_cases.update_investment(investment_id, self._dto_from_dialog(dialog.get_data()))
            self._on_changed()

    def _open_transactions(self, investment_id):
        investment = self._use_cases.get_investment(investment_id)
        if investment is None:
            return
        dialog = InvestmentTransactionsDialog(self, investment, self._use_cases)
        dialog.exec()
        self._on_changed()

    def _open_schedules(self, investment_id):
        investment = self._use_cases.get_investment(investment_id)
        if investment is None:
            return
        dialog = InvestmentSchedulesDialog(self, investment, self._use_cases)
        dialog.exec()
        if dialog.changed():
            self._on_changed()
        else:
            self.refresh()

    def _update_price(self, investment_id):
        investment = self._use_cases.get_investment(investment_id)
        if investment is None:
            return
        price, ok = QInputDialog.getDouble(
            self, t("investments.update_price.title"),
            t("investments.update_price.label", name=investment.name),
            investment.current_price, 0, 1_000_000_000, 2,
        )
        if ok:
            self._use_cases.update_price(investment_id, price)
            self._on_changed()

    def _delete_investment(self, investment_id):
        investment = self._use_cases.get_investment(investment_id)
        if investment is None:
            return
        reply = QMessageBox.question(
            self, t("mainwindow.msg.delete_investment.title"),
            t("mainwindow.msg.delete_investment.body", name=investment.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._use_cases.delete_investment(investment_id)
        self._on_changed()

    def _on_changed(self):
        self.refresh()
        self.changed.emit()
