from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.domain.entities.financial_event import EventType
from src.domain.services.account_summary_service import AccountSummaryService
from src.presentation import icons, theme
from src.presentation.i18n import format_currency, format_date, t
from src.presentation.labels import event_type_label, event_type_choices
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from src.presentation.widgets.stat_card import make_stat_card

# Event types that increase the account's balance when the event belongs to it.
# A TRANSFER is handled separately (its direction depends on which side the
# account sits on), so it is deliberately absent here.
_INFLOW_TYPES = {
    EventType.INCOME.value,
    EventType.REFUND.value,
    EventType.REDEMPTION.value,
}


class AccountDetailWidget(QWidget):
    """Per-account detail screen: the account's current balance plus a
    filterable listing of every event touching it (its own events and any
    transfer into it). Shown as a dedicated tab, populated via set_account().

    The current balance is always the true all-time balance (reusing
    AccountSummaryService); the date range, type, category and search filters
    only scope the event listing and the period in/out stat cards.

    Emits back_requested when the user asks to leave the screen (it is not a
    tab, so it owns its own way back to the Accounts listing).
    """

    back_requested = Signal()
    # Row double-click asks the host to open the matching edit modal.
    edit_event_requested = Signal(str)
    edit_recurring_requested = Signal(str)

    def __init__(
        self,
        account_summary_service: AccountSummaryService,
        financial_event_use_cases,
        account_use_cases,
        category_use_cases,
        counterparty_use_cases,
        recurring_event_use_cases,
    ):
        super().__init__()
        self._summary_service = account_summary_service
        self._event_use_cases = financial_event_use_cases
        self._account_use_cases = account_use_cases
        self._category_use_cases = category_use_cases
        self._counterparty_use_cases = counterparty_use_cases
        self._recurring_event_use_cases = recurring_event_use_cases
        self._account_id: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        back_btn = QPushButton(t("account_detail.back"))
        back_btn.setIcon(icons.icon("fa6s.arrow-left"))
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)

        self._header = QLabel(t("account_detail.select_prompt"))
        self._header.setObjectName("sectionTitle")
        header_row.addWidget(self._header)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Filter row: date range + type + category + search.
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(t("account_detail.period")))
        self._date_range = DateRangeSelector(default_label="All Time")
        self._date_range.range_changed.connect(lambda _d: self.refresh())
        filter_row.addWidget(self._date_range)

        filter_row.addWidget(QLabel(t("account_detail.filter_type")))
        self._type_filter = QComboBox()
        self._type_filter.addItem(t("account_detail.all_types"), None)
        for member, label in event_type_choices():
            self._type_filter.addItem(label, member)
        self._type_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        filter_row.addWidget(self._type_filter)

        filter_row.addWidget(QLabel(t("account_detail.filter_category")))
        self._category_filter = QComboBox()
        self._category_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        filter_row.addWidget(self._category_filter)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("account_detail.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        filter_row.addWidget(self._search)

        btn_search = QPushButton(t("common.search"))
        btn_search.setIcon(icons.icon("fa6s.magnifying-glass"))
        btn_search.clicked.connect(self.refresh)
        filter_row.addWidget(btn_search)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Stat cards.
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._balance_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("account_detail.current_balance"), self._balance_label))

        self._income_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("account_detail.period_income"), self._income_label))

        self._expenses_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("account_detail.period_expenses"), self._expenses_label))

        layout.addLayout(cards_layout)

        # Event listing.
        self._table = EvenColumnsTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            t("common.date"), t("common.type"), t("common.description"),
            t("common.category"), t("mainwindow.table.events.header.counterparty"),
            t("common.amount"),
        ])
        self._table.setObjectName("mainTabTable")
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.cellDoubleClicked.connect(self._on_row_activated)
        layout.addWidget(self._table)

    def set_account(self, account_id: str):
        """Point the screen at an account and refresh its data."""
        self._account_id = account_id
        self.refresh()

    def has_account(self) -> bool:
        return self._account_id is not None

    def _populate_category_filter(self):
        self._category_filter.blockSignals(True)
        prev = self._category_filter.currentData()
        self._category_filter.clear()
        self._category_filter.addItem(t("mainwindow.filter.all_categories"), None)
        for cat in self._category_use_cases.list_categories():
            self._category_filter.addItem(cat.name, cat.id)
        if prev is not None:
            idx = self._category_filter.findData(prev)
            if idx >= 0:
                self._category_filter.setCurrentIndex(idx)
        self._category_filter.blockSignals(False)

    def _direction(self, event) -> int:
        """+1 if the event increases this account's balance, -1 if it lowers it."""
        if event.event_type == EventType.TRANSFER.value:
            return 1 if event.destination_account_id == self._account_id else -1
        return 1 if event.event_type in _INFLOW_TYPES else -1

    def _type_display(self, event, accounts_map) -> str:
        label = event_type_label(event.event_type)
        if event.event_type == EventType.TRANSFER.value:
            if event.account_id == self._account_id and event.destination_account_id:
                other = accounts_map.get(event.destination_account_id, "")
                label = t("account_detail.transfer_out", name=other)
            elif event.destination_account_id == self._account_id:
                other = accounts_map.get(event.account_id, "")
                label = t("account_detail.transfer_in", name=other)
        return label

    def refresh(self):
        if self._account_id is None:
            self._header.setText(t("account_detail.select_prompt"))
            self._table.setRowCount(0)
            return

        self._populate_category_filter()

        accounts_map = {a.id: a.name for a in self._account_use_cases.list_accounts()}
        categories_map = {c.id: c.name for c in self._category_use_cases.list_categories()}
        counterparties_map = {
            c.id: c.name for c in self._counterparty_use_cases.list_counterparties()
        }

        account_name = accounts_map.get(self._account_id, "")
        self._header.setText(t("account_detail.header", name=account_name))

        date_from, date_to = self._date_range.resolved_range()
        # The repository treats date_to as an exclusive upper bound, but
        # resolved_range()'s date_to is inclusive of that whole day.
        date_to_exclusive = date_to + timedelta(days=1) if date_to else None

        self._refresh_cards(date_from, date_to_exclusive)
        self._refresh_table(date_from, date_to_exclusive, accounts_map, categories_map, counterparties_map)

    def _refresh_cards(self, date_from, date_to_exclusive):
        # Current balance is always the true all-time balance, independent of
        # the period filter; only the in/out cards below are period-scoped.
        all_time = self._find_item(self._summary_service.get_summary())
        current_balance = all_time.current_balance if all_time else 0.0
        self._balance_label.setText(format_currency(current_balance, "BRL"))
        self._balance_label.setStyleSheet(
            f"color: {theme.INCOME if current_balance >= 0 else theme.EXPENSE};"
        )

        period = self._find_item(
            self._summary_service.get_summary(date_from=date_from, date_to=date_to_exclusive)
        )
        # For a single account both real income and incoming transfers raise the
        # balance, and both spending and outgoing transfers lower it - so the
        # per-account in/out cards combine them into intuitive cash-flow totals.
        inflow = (period.total_income + period.transfer_in) if period else 0.0
        outflow = (period.total_expenses + period.transfer_out) if period else 0.0
        self._income_label.setText(format_currency(inflow, "BRL"))
        self._income_label.setStyleSheet(f"color: {theme.INCOME};")
        self._expenses_label.setText(format_currency(outflow, "BRL"))
        self._expenses_label.setStyleSheet(f"color: {theme.EXPENSE};")

    def _find_item(self, summary):
        for item in summary.items:
            if item.account_id == self._account_id:
                return item
        return None

    def _refresh_table(self, date_from, date_to_exclusive, accounts_map, categories_map, counterparties_map):
        event_type = self._type_filter.currentData()
        category_id = self._category_filter.currentData()
        description = self._search.text().strip() or None

        events = self._event_use_cases.list_events(
            date_from=date_from,
            date_to=date_to_exclusive,
            event_type=event_type,
            category_id=category_id,
            account_id=self._account_id,
            description=description,
        )
        occurrences = self._pending_occurrences(
            date_from, date_to_exclusive, event_type, category_id, description
        )

        # Real events first, then virtual (pending) occurrences, newest first -
        # same listing convention as the main Events tab.
        rows = [(e, False) for e in events] + [(o, True) for o in occurrences]
        rows.sort(key=lambda r: r[0].event_date, reverse=True)

        self._table.setRowCount(len(rows))
        for i, (payload, is_virtual) in enumerate(rows):
            self._populate_row(i, payload, is_virtual, accounts_map, categories_map, counterparties_map)

        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _pending_occurrences(self, date_from, date_to_exclusive, event_type, category_id, description):
        # Pending occurrences project into the future, so an open-ended range
        # (the "All Time" default gives date_from/date_to = None) must be bounded
        # or generation would never terminate. Mirror the Events tab's behavior:
        # show occurrences that are due but not yet confirmed, up to today when
        # no explicit upper bound is set.
        occ_from = date_from or date.min
        occ_to = date_to_exclusive or (date.today() + timedelta(days=1))
        occurrences = self._recurring_event_use_cases.get_pending_occurrences(
            occ_from, occ_to,
            category_id=category_id,
            account_id=self._account_id,
            description=description,
        )
        # get_pending_occurrences has no event_type filter, so apply it here to
        # keep the Type filter consistent with the real-event rows.
        if event_type is not None:
            occurrences = [o for o in occurrences if o.event_type == event_type.value]
        return occurrences

    def _on_row_activated(self, row, _col):
        item = self._table.item(row, 0)
        if item is None:
            return
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        kind, ident = payload
        if kind == "recurring":
            self.edit_recurring_requested.emit(ident)
        else:
            self.edit_event_requested.emit(ident)

    def _populate_row(self, i, e, is_virtual, accounts_map, categories_map, counterparties_map):
        type_label = self._type_display(e, accounts_map)
        if is_virtual:
            type_label = t("mainwindow.events.recurring_suffix", type=type_label)

        self._table.setItem(i, 0, QTableWidgetItem(format_date(e.event_date)))
        self._table.setItem(i, 1, QTableWidgetItem(type_label))
        self._table.setItem(i, 2, QTableWidgetItem(e.description))
        self._table.setItem(i, 3, QTableWidgetItem(categories_map.get(e.category_id, "")))
        self._table.setItem(i, 4, QTableWidgetItem(counterparties_map.get(e.counterparty_id, "")))

        direction = self._direction(e)
        sign = "+" if direction > 0 else "-"
        amount_item = QTableWidgetItem(f"{sign}{format_currency(abs(e.amount), e.currency)}")
        amount_item.setForeground(QColor(theme.INCOME if direction > 0 else theme.EXPENSE))
        self._table.setItem(i, 5, amount_item)

        # Stash what a double-click should edit: the recurring template for a
        # pending occurrence, the event itself otherwise.
        if is_virtual:
            self._table.item(i, 0).setData(Qt.UserRole, ("recurring", e.recurring_event_id))
        else:
            self._table.item(i, 0).setData(Qt.UserRole, ("event", e.id))

        if is_virtual:
            # Italicize pending (not-yet-confirmed) occurrences to set them apart
            # from real events, matching the Events tab.
            italic = QFont()
            italic.setItalic(True)
            for col in range(6):
                self._table.item(i, col).setFont(italic)
