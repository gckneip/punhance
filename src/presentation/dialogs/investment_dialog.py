from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox, QDateEdit, QDoubleSpinBox,
    QDialogButtonBox, QHBoxLayout, QVBoxLayout, QMessageBox, QWidget,
)

from src.presentation.i18n import CURRENCIES, CURRENCY_SYMBOLS, t
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.presentation.labels import asset_type_choices
from src.domain.entities.investment import AssetType, YieldIndex


class InvestmentDialog(QDialog):
    def __init__(self, parent=None, investment=None, accounts=None, force_asset_type=None):
        super().__init__(parent)
        self._force_asset_type = force_asset_type
        self.setWindowTitle(
            t("investment_dialog.title_edit") if investment else t("investment_dialog.title_create")
        )
        self.setModal(True)
        self.resize(380, 340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow(f'{t("common.name")}:', self.name_edit)

        self.type_combo = QComboBox()
        for member, label in asset_type_choices():
            self.type_combo.addItem(label, member)
        if force_asset_type is not None:
            fidx = self.type_combo.findData(force_asset_type)
            if fidx >= 0:
                self.type_combo.setCurrentIndex(fidx)
            # Launched from a type-specific tab (e.g. Caixinhas): lock the type.
            self.type_combo.setEnabled(False)
        form.addRow(t("investment_dialog.asset_type"), self.type_combo)

        self.ticker_edit = QLineEdit()
        form.addRow(t("investment_dialog.ticker"), self.ticker_edit)

        self.currency_combo = QComboBox()
        for code in CURRENCIES:
            self.currency_combo.addItem(code, code)
        form.addRow(t("investment_dialog.currency"), self.currency_combo)

        self.account_combo = QComboBox()
        self.account_combo.addItem(t("investment_dialog.no_account"), None)
        for acc in (accounts or []):
            self.account_combo.addItem(acc.name, acc.id)
        form.addRow(t("investment_dialog.account"), self.account_combo)

        self.price_spin = CurrencySpinBox()
        self.price_spin.setRange(0, 99999999)
        self.price_spin.setPrefix(CURRENCY_SYMBOLS["BRL"] + " ")
        form.addRow(t("investment_dialog.current_price"), self.price_spin)

        # Yield (for income/value projections) — shown for all asset types.
        yield_row = QWidget()
        yield_layout = QHBoxLayout(yield_row)
        yield_layout.setContentsMargins(0, 0, 0, 0)
        self.yield_rate_spin = QDoubleSpinBox()
        self.yield_rate_spin.setRange(0, 10000)
        self.yield_rate_spin.setDecimals(2)
        self.yield_rate_spin.setSuffix(" %")
        self.yield_index_combo = QComboBox()
        for member in YieldIndex:
            self.yield_index_combo.addItem(t(f"investment.yield_index.{member.value}"), member.value)
        yield_layout.addWidget(self.yield_rate_spin)
        yield_layout.addWidget(self.yield_index_combo)
        form.addRow(t("investment_dialog.yield"), yield_row)

        # Maturity/redemption date (fixed income, e.g. Tesouro Selic). Optional.
        self._maturity_row = maturity_row = QWidget()
        maturity_layout = QHBoxLayout(maturity_row)
        maturity_layout.setContentsMargins(0, 0, 0, 0)
        self.maturity_check = QCheckBox(t("investment_dialog.maturity_enable"))
        self.maturity_edit = QDateEdit()
        self.maturity_edit.setCalendarPopup(True)
        self.maturity_edit.setDate(QDate.currentDate())
        self.maturity_edit.setEnabled(False)
        self.maturity_check.toggled.connect(self.maturity_edit.setEnabled)
        maturity_layout.addWidget(self.maturity_check)
        maturity_layout.addWidget(self.maturity_edit)
        form.addRow(t("investment_dialog.maturity"), maturity_row)

        # Savings-box goal (Caixinha/Cofrinho): only shown for the SAVINGS_BOX type.
        self.goal_spin = CurrencySpinBox()
        self.goal_spin.setRange(0, 99999999)
        self.goal_spin.setPrefix(CURRENCY_SYMBOLS["BRL"] + " ")
        form.addRow(t("investment_dialog.goal_amount"), self.goal_spin)

        self._goal_date_row = QWidget()
        goal_date_layout = QHBoxLayout(self._goal_date_row)
        goal_date_layout.setContentsMargins(0, 0, 0, 0)
        self.goal_date_check = QCheckBox(t("investment_dialog.goal_date_enable"))
        self.goal_date_edit = QDateEdit()
        self.goal_date_edit.setCalendarPopup(True)
        self.goal_date_edit.setDate(QDate.currentDate())
        self.goal_date_edit.setEnabled(False)
        self.goal_date_check.toggled.connect(self.goal_date_edit.setEnabled)
        goal_date_layout.addWidget(self.goal_date_check)
        goal_date_layout.addWidget(self.goal_date_edit)
        form.addRow(t("investment_dialog.goal_date"), self._goal_date_row)

        self.monthly_contribution_spin = CurrencySpinBox()
        self.monthly_contribution_spin.setRange(0, 99999999)
        self.monthly_contribution_spin.setPrefix(CURRENCY_SYMBOLS["BRL"] + " ")
        form.addRow(t("investment_dialog.monthly_contribution"), self.monthly_contribution_spin)

        self._form = form

        self.notes_edit = QLineEdit()
        form.addRow(t("common.notes"), self.notes_edit)

        self.active_check = QCheckBox(t("investment_dialog.active"))
        self.active_check.setChecked(True)
        form.addRow("", self.active_check)

        layout.addLayout(form)

        # Keep the price field's currency prefix in sync with the chosen currency.
        self.currency_combo.currentTextChanged.connect(self._sync_price_prefix)
        # Goal fields only make sense for savings boxes.
        self.type_combo.currentIndexChanged.connect(self._sync_goal_visibility)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if investment is not None:
            self.name_edit.setText(investment.name)
            idx = self.type_combo.findData(investment.asset_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.ticker_edit.setText(investment.ticker or "")
            cidx = self.currency_combo.findData(investment.currency)
            if cidx >= 0:
                self.currency_combo.setCurrentIndex(cidx)
            aidx = self.account_combo.findData(investment.account_id)
            if aidx >= 0:
                self.account_combo.setCurrentIndex(aidx)
            self.price_spin.setValue(investment.current_price)
            if investment.yield_rate:
                self.yield_rate_spin.setValue(investment.yield_rate)
            yidx = self.yield_index_combo.findData(investment.yield_index or "prefixed")
            if yidx >= 0:
                self.yield_index_combo.setCurrentIndex(yidx)
            if investment.monthly_contribution:
                self.monthly_contribution_spin.setValue(investment.monthly_contribution)
            if investment.maturity_date:
                self.maturity_check.setChecked(True)
                mqdate = QDate.fromString(investment.maturity_date, "yyyy-MM-dd")
                if mqdate.isValid():
                    self.maturity_edit.setDate(mqdate)
            if investment.goal_amount:
                self.goal_spin.setValue(investment.goal_amount)
            if investment.goal_date:
                self.goal_date_check.setChecked(True)
                qdate = QDate.fromString(investment.goal_date, "yyyy-MM-dd")
                if qdate.isValid():
                    self.goal_date_edit.setDate(qdate)
            self.notes_edit.setText(investment.notes or "")
            self.active_check.setChecked(investment.is_active)
        self._sync_price_prefix()
        self._sync_goal_visibility()

    def _sync_price_prefix(self):
        code = self.currency_combo.currentData() or "BRL"
        prefix = CURRENCY_SYMBOLS.get(code, code) + " "
        self.price_spin.setPrefix(prefix)
        self.goal_spin.setPrefix(prefix)
        self.monthly_contribution_spin.setPrefix(prefix)

    def _sync_goal_visibility(self):
        is_box = self.type_combo.currentData() == AssetType.SAVINGS_BOX
        self._form.setRowVisible(self.goal_spin, is_box)
        self._form.setRowVisible(self._goal_date_row, is_box)
        self._form.setRowVisible(self.monthly_contribution_spin, is_box)
        # A savings box has a balance, not a ticker or a fixed maturity; and its
        # "current price" is really its current balance.
        self._form.setRowVisible(self.ticker_edit, not is_box)
        self._form.setRowVisible(self._maturity_row, not is_box)
        price_label = self._form.labelForField(self.price_spin)
        if price_label is not None:
            price_label.setText(
                t("investment_dialog.current_balance") if is_box
                else t("investment_dialog.current_price")
            )

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, t("common.warning"), t("investment_dialog.name_required"))
            return
        self.accept()

    def get_data(self):
        is_box = self.type_combo.currentData() == AssetType.SAVINGS_BOX
        goal_amount = self.goal_spin.value() if (is_box and self.goal_spin.value()) else None
        goal_date = (
            self.goal_date_edit.date().toString("yyyy-MM-dd")
            if (is_box and self.goal_date_check.isChecked())
            else None
        )
        return {
            "name": self.name_edit.text().strip(),
            "asset_type": self.type_combo.currentData(),
            "ticker": self.ticker_edit.text().strip() or None,
            "currency": self.currency_combo.currentData() or "BRL",
            "account_id": self.account_combo.currentData(),
            "current_price": self.price_spin.value(),
            "goal_amount": goal_amount,
            "goal_date": goal_date,
            "yield_rate": self.yield_rate_spin.value() or None,
            "yield_index": self.yield_index_combo.currentData() or "prefixed",
            "monthly_contribution": (
                self.monthly_contribution_spin.value() if (is_box and self.monthly_contribution_spin.value()) else None
            ),
            "maturity_date": (
                self.maturity_edit.date().toString("yyyy-MM-dd") if self.maturity_check.isChecked() else None
            ),
            "notes": self.notes_edit.text().strip() or None,
            "is_active": self.active_check.isChecked(),
        }
