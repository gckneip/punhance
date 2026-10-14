from datetime import date

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QMessageBox, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.presentation import icons, theme
from src.presentation.i18n import format_currency, format_date, format_number, t
from src.presentation.dialogs.investment_dialog import InvestmentDialog
from src.presentation.dialogs.investment_transactions_dialog import InvestmentTransactionsDialog
from src.presentation.dialogs.investment_schedules_dialog import InvestmentSchedulesDialog
from src.presentation.dialogs.savings_box_movement_dialog import SavingsBoxMovementDialog
from src.application.dto.investment_dto import CreateInvestmentDTO
from src.application.dto.financial_event_dto import CreateFinancialEventDTO
from src.domain.entities.investment import AssetType
from src.domain.entities.financial_event import EventType


class CaixinhasPanel(QWidget):
    """Manage savings boxes (Caixinha/Cofrinho) with box-appropriate concepts.

    A savings box is a single balance you add to and withdraw from — not a
    quantity of priced units — so this panel shows Balance / Contributed / Yield
    / Goal instead of the quantity, average-price and unit-price columns of the
    assets portfolio, and offers plain deposit/withdraw/update-balance actions.

    Yield is the balance minus the net contributed; deposits and withdrawals move
    both together (leaving yield unchanged), and "update balance" records the
    interest the bank has actually credited.
    """

    changed = Signal()

    def __init__(
        self, investment_use_cases, account_use_cases,
        financial_event_use_cases=None, parent=None,
    ):
        super().__init__(parent)
        self._use_cases = investment_use_cases
        self._account_use_cases = account_use_cases
        self._financial_event_use_cases = financial_event_use_cases

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(t("caixinhas.add"))
        add_btn.setIcon(icons.icon("fa6s.circle-plus"))
        add_btn.clicked.connect(self._add_box)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            t("common.name"),
            t("caixinhas.header.balance"),
            t("caixinhas.header.contributed"),
            t("caixinhas.header.yield"),
            t("caixinhas.header.goal"),
            t("caixinhas.header.updated"),
            t("common.actions"),
        ])
        self._table.setObjectName("mainTabTable")
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self.refresh()

    # -- data -----------------------------------------------------------------

    def _boxes(self):
        return [
            inv for inv in self._use_cases.list_investments()
            if inv.asset_type == AssetType.SAVINGS_BOX
        ]

    def refresh(self):
        boxes = self._boxes()
        self._table.setRowCount(len(boxes))
        for i, box in enumerate(boxes):
            balance = box.current_price
            contributed = box.net_invested
            box_yield = balance - contributed

            self._table.setItem(i, 0, QTableWidgetItem(box.name))
            self._table.setItem(i, 1, QTableWidgetItem(format_currency(balance, box.currency)))
            self._table.setItem(i, 2, QTableWidgetItem(format_currency(contributed, box.currency)))

            pct = (box_yield / contributed * 100.0) if contributed > 0 else 0.0
            yield_item = QTableWidgetItem(
                f"{format_currency(box_yield, box.currency)} ({format_number(pct, 1)}%)"
            )
            if box_yield > 0:
                yield_item.setForeground(QColor(theme.INCOME))
            elif box_yield < 0:
                yield_item.setForeground(QColor(theme.EXPENSE))
            self._table.setItem(i, 3, yield_item)

            if box.goal_amount:
                self._table.setCellWidget(i, 4, self._goal_cell(box, balance))
            else:
                self._table.setItem(i, 4, QTableWidgetItem(t("caixinhas.goal.none")))

            self._table.setItem(i, 5, QTableWidgetItem(
                format_date(box.price_updated_at[:10]) if box.price_updated_at else ""))
            self._table.setCellWidget(i, 6, self._make_actions(box.id))
        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _goal_cell(self, box, balance):
        pct = min(balance / box.goal_amount * 100.0, 100.0) if box.goal_amount else 0.0
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(round(pct)))
        bar.setFormat(f"{format_number(pct, 0)}%")
        bar.setTextVisible(True)
        bar.setMinimumWidth(150)
        bar.setToolTip(
            f"{format_currency(balance, box.currency)} / "
            f"{format_currency(box.goal_amount, box.currency)}"
        )
        return bar

    def _make_actions(self, box_id):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(4)
        for label, icon_name, handler in (
            (t("caixinhas.action.deposit"), "fa6s.money-bill-trend-up",
             lambda: self._move(box_id, "deposit")),
            (t("caixinhas.action.withdraw"), "fa6s.money-bill-wave",
             lambda: self._move(box_id, "withdraw")),
            (t("caixinhas.action.update_balance"), "fa6s.pen-to-square",
             lambda: self._update_balance(box_id)),
            (t("investments.action.transactions"), "fa6s.list",
             lambda: self._open_transactions(box_id)),
            (t("investments.action.schedule"), "fa6s.calendar-plus",
             lambda: self._open_schedules(box_id)),
            (t("common.edit"), "fa6s.pen", lambda: self._edit_box(box_id)),
            (t("common.delete"), "fa6s.trash", lambda: self._delete_box(box_id)),
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

    # -- actions --------------------------------------------------------------

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

    def _add_box(self):
        accounts = self._account_use_cases.list_accounts()
        dialog = InvestmentDialog(self, accounts=accounts, force_asset_type=AssetType.SAVINGS_BOX)
        if dialog.exec():
            self._use_cases.create_investment(self._dto_from_dialog(dialog.get_data()))
            self._on_changed()

    def _edit_box(self, box_id):
        box = self._use_cases.get_investment(box_id)
        if box is None:
            return
        accounts = self._account_use_cases.list_accounts()
        dialog = InvestmentDialog(self, investment=box, accounts=accounts)
        if dialog.exec():
            self._use_cases.update_investment(box_id, self._dto_from_dialog(dialog.get_data()))
            self._on_changed()

    def _move(self, box_id, direction):
        box = self._use_cases.get_investment(box_id)
        if box is None:
            return
        accounts = self._account_use_cases.list_accounts()
        dialog = SavingsBoxMovementDialog(self, box, direction, accounts=accounts)
        if not dialog.exec():
            return
        data = dialog.get_data()
        self._use_cases.add_savings_movement(
            box_id, direction, data["amount"], data["date"], data["notes"],
        )
        self._use_cases.record_snapshot()
        self._apply_account_movement(box, direction, data)
        self._on_changed()

    def _apply_account_movement(self, box, direction, data):
        """Mirror the movement as a finance event so the cash actually leaves /
        lands in the chosen account: a deposit debits it, a withdrawal credits it."""
        if self._financial_event_use_cases is None:
            return
        account_id = data.get("account_id")
        if not account_id or data["amount"] <= 0:
            return
        if direction == "withdraw":
            event_type = EventType.REDEMPTION
            description = t("invest_action.redeem_description", name=box.name)
        else:
            event_type = EventType.INVESTMENT
            description = t("invest_action.invest_description", name=box.name)
        self._financial_event_use_cases.create_event(CreateFinancialEventDTO(
            event_type=event_type,
            event_date=date.fromisoformat(data["date"]),
            description=description,
            amount=data["amount"],
            account_id=account_id,
            currency=box.currency,
            notes=data["notes"],
        ))

    def _update_balance(self, box_id):
        box = self._use_cases.get_investment(box_id)
        if box is None:
            return
        balance, ok = QInputDialog.getDouble(
            self, t("caixinhas.update_balance.title"),
            t("caixinhas.update_balance.label", name=box.name),
            box.current_price, 0, 1_000_000_000, 2,
        )
        if ok:
            self._use_cases.update_price(box_id, balance)
            self._on_changed()

    def _open_transactions(self, box_id):
        box = self._use_cases.get_investment(box_id)
        if box is None:
            return
        InvestmentTransactionsDialog(self, box, self._use_cases).exec()
        self._on_changed()

    def _open_schedules(self, box_id):
        box = self._use_cases.get_investment(box_id)
        if box is None:
            return
        dialog = InvestmentSchedulesDialog(self, box, self._use_cases)
        dialog.exec()
        if dialog.changed():
            self._on_changed()
        else:
            self.refresh()

    def _delete_box(self, box_id):
        box = self._use_cases.get_investment(box_id)
        if box is None:
            return
        reply = QMessageBox.question(
            self, t("mainwindow.msg.delete_investment.title"),
            t("mainwindow.msg.delete_investment.body", name=box.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._use_cases.delete_investment(box_id)
        self._on_changed()

    def _on_changed(self):
        self.refresh()
        self.changed.emit()
