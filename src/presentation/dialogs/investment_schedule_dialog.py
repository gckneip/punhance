from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QMessageBox, QSpinBox, QVBoxLayout, QWidget,
)

from src.presentation.i18n import CURRENCY_SYMBOLS, t
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.domain.entities.investment_schedule import ScheduleFrequency


class InvestmentScheduleDialog(QDialog):
    """Create/edit one recurring contribution rule for an investment."""

    def __init__(self, parent=None, schedule=None, currency="BRL"):
        super().__init__(parent)
        self.setWindowTitle(
            t("investment_schedule_dialog.title_edit") if schedule
            else t("investment_schedule_dialog.title_create")
        )
        self.setModal(True)
        self.resize(360, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.amount_spin = CurrencySpinBox()
        self.amount_spin.setRange(0, 99999999)
        self.amount_spin.setPrefix(CURRENCY_SYMBOLS.get(currency, currency) + " ")
        form.addRow(t("investment_schedule_dialog.amount"), self.amount_spin)

        self.frequency_combo = QComboBox()
        for member in ScheduleFrequency:
            self.frequency_combo.addItem(t(f"enum.recurrence.{member.value}"), member)
        form.addRow(t("investment_schedule_dialog.frequency"), self.frequency_combo)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 365)
        self.interval_spin.setValue(1)
        form.addRow(t("investment_schedule_dialog.interval"), self.interval_spin)

        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDate(QDate.currentDate())
        form.addRow(t("investment_schedule_dialog.start_date"), self.start_edit)

        end_row = QWidget()
        end_layout = QHBoxLayout(end_row)
        end_layout.setContentsMargins(0, 0, 0, 0)
        self.end_check = QCheckBox(t("investment_schedule_dialog.end_enable"))
        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDate(QDate.currentDate())
        self.end_edit.setEnabled(False)
        self.end_check.toggled.connect(self.end_edit.setEnabled)
        end_layout.addWidget(self.end_check)
        end_layout.addWidget(self.end_edit)
        form.addRow(t("investment_schedule_dialog.end_date"), end_row)

        self.active_check = QCheckBox(t("investment_schedule_dialog.active"))
        self.active_check.setChecked(True)
        form.addRow("", self.active_check)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if schedule is not None:
            self.amount_spin.setValue(schedule.amount)
            idx = self.frequency_combo.findData(schedule.frequency)
            if idx >= 0:
                self.frequency_combo.setCurrentIndex(idx)
            self.interval_spin.setValue(schedule.interval)
            sq = QDate.fromString(schedule.start_date, "yyyy-MM-dd")
            if sq.isValid():
                self.start_edit.setDate(sq)
            if schedule.end_date:
                self.end_check.setChecked(True)
                eq = QDate.fromString(schedule.end_date, "yyyy-MM-dd")
                if eq.isValid():
                    self.end_edit.setDate(eq)
            self.active_check.setChecked(schedule.is_active)

    def _validate_and_accept(self):
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(
                self, t("common.warning"), t("investment_schedule_dialog.amount_required")
            )
            return
        self.accept()

    def get_data(self):
        return {
            "amount": self.amount_spin.value(),
            "frequency": self.frequency_combo.currentData(),
            "interval": self.interval_spin.value(),
            "start_date": self.start_edit.date().toString("yyyy-MM-dd"),
            "end_date": (
                self.end_edit.date().toString("yyyy-MM-dd") if self.end_check.isChecked() else None
            ),
            "is_active": self.active_check.isChecked(),
        }
