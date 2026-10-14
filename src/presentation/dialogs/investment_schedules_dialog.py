from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.presentation import icons
from src.presentation.i18n import format_currency, format_date, t
from src.presentation.dialogs.investment_schedule_dialog import InvestmentScheduleDialog
from src.application.dto.investment_schedule_dto import CreateInvestmentScheduleDTO


class InvestmentSchedulesDialog(QDialog):
    """Manage the recurring contribution schedules of one investment. Materializes
    any newly-due contributions immediately after edits."""

    def __init__(self, parent, investment, investment_use_cases):
        super().__init__(parent)
        self._investment = investment
        self._use_cases = investment_use_cases
        self._changed = False

        self.setWindowTitle(t("investment_schedules.title", name=investment.name))
        self.setModal(True)
        self.resize(560, 380)

        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(t("investment_schedules.add"))
        add_btn.setIcon(icons.icon("fa6s.circle-plus"))
        add_btn.clicked.connect(self._add_schedule)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            t("investment_schedule_dialog.frequency"),
            t("investment_schedule_dialog.amount"),
            t("investment_schedules.next"),
            t("mainwindow.table.header.active"),
            t("common.actions"),
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh()

    def changed(self) -> bool:
        return self._changed

    def _freq_label(self, sched) -> str:
        base = t(f"enum.recurrence.{sched.frequency.value}")
        if sched.interval and sched.interval != 1:
            return t("investment_schedules.every", n=sched.interval, freq=base)
        return base

    def _refresh(self):
        schedules = self._use_cases.list_schedules(self._investment.id)
        self._table.setRowCount(len(schedules))
        for i, s in enumerate(schedules):
            self._table.setItem(i, 0, QTableWidgetItem(self._freq_label(s)))
            self._table.setItem(i, 1, QTableWidgetItem(
                format_currency(s.amount, self._investment.currency)))
            self._table.setItem(i, 2, QTableWidgetItem(
                format_date(s.next_date) if s.next_date else "—"))
            self._table.setItem(i, 3, QTableWidgetItem(
                t("common.yes") if s.is_active else t("common.no")))
            self._table.setCellWidget(i, 4, self._make_actions(s))
        self._table.resizeColumnsToContents()

    def _make_actions(self, schedule):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(4)
        for label, icon_name, handler in (
            (t("common.edit"), "fa6s.pen", lambda: self._edit_schedule(schedule)),
            (t("common.delete"), "fa6s.trash", lambda: self._delete_schedule(schedule)),
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
        return CreateInvestmentScheduleDTO(
            investment_id=self._investment.id,
            amount=data["amount"],
            frequency=data["frequency"],
            start_date=data["start_date"],
            interval=data["interval"],
            end_date=data["end_date"],
            is_active=data["is_active"],
        )

    def _after_change(self):
        # Materialize any now-due contributions immediately.
        self._use_cases.generate_due_schedules()
        self._changed = True
        self._refresh()

    def _add_schedule(self):
        dialog = InvestmentScheduleDialog(self, currency=self._investment.currency)
        if dialog.exec():
            self._use_cases.add_schedule(self._dto_from_dialog(dialog.get_data()))
            self._after_change()

    def _edit_schedule(self, schedule):
        dialog = InvestmentScheduleDialog(self, schedule=schedule, currency=self._investment.currency)
        if dialog.exec():
            self._use_cases.update_schedule(schedule.id, self._dto_from_dialog(dialog.get_data()))
            self._after_change()

    def _delete_schedule(self, schedule):
        reply = QMessageBox.question(
            self, t("investment_schedules.delete_title"), t("investment_schedules.delete_body"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._use_cases.delete_schedule(schedule.id)
        self._changed = True
        self._refresh()
