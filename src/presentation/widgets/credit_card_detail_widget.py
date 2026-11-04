from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.domain.entities.financial_event import EventType
from src.presentation import icons, theme
from src.presentation.i18n import format_currency, format_date, t
from src.presentation.labels import event_type_label, event_type_choices
from src.presentation.widgets.date_range_selector import DateRangeSelector
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from src.presentation.widgets.stat_card import make_stat_card


class CreditCardDetailWidget(QWidget):
    """Per-card detail screen: the card's current debt / available credit plus
    a filterable listing of every charge and payment on it. Shown as a second
    page of the Credit Cards tab, populated via set_card().

    The debt/credit stat cards always reflect the true all-time status
    (reusing CreditCardService via get_status); the date range, type, category
    and search filters only scope the charge listing.

    Emits back_requested when the user asks to return to the cards listing.
    """

    back_requested = Signal()
    # Row double-click asks the host to open the matching edit modal.
    edit_event_requested = Signal(str)
    edit_recurring_requested = Signal(str)
    # "Pay invoice" button asks the host to open the card-payment flow for the
    # currently shown card (emits its id).
    pay_card_requested = Signal(str)

    def __init__(
        self,
        credit_card_use_cases,
        financial_event_use_cases,
        category_use_cases,
        counterparty_use_cases,
        recurring_event_use_cases,
    ):
        super().__init__()
        self._card_use_cases = credit_card_use_cases
        self._event_use_cases = financial_event_use_cases
        self._category_use_cases = category_use_cases
        self._counterparty_use_cases = counterparty_use_cases
        self._recurring_event_use_cases = recurring_event_use_cases
        self._card_id: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        back_btn = QPushButton(t("credit_card_detail.back"))
        back_btn.setIcon(icons.icon("fa6s.arrow-left"))
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)

        self._header = QLabel(t("credit_card_detail.select_prompt"))
        self._header.setObjectName("sectionTitle")
        header_row.addWidget(self._header)
        header_row.addStretch()

        self._pay_btn = QPushButton(t("credit_card_detail.pay"))
        self._pay_btn.setIcon(icons.icon("fa6s.money-bill-wave"))
        self._pay_btn.clicked.connect(self._on_pay_clicked)
        header_row.addWidget(self._pay_btn)
        layout.addLayout(header_row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(t("credit_card_detail.period")))
        self._date_range = DateRangeSelector(default_label="All Time")
        self._date_range.range_changed.connect(lambda _d: self.refresh())
        filter_row.addWidget(self._date_range)

        filter_row.addWidget(QLabel(t("credit_card_detail.filter_type")))
        self._type_filter = QComboBox()
        self._type_filter.addItem(t("credit_card_detail.all_types"), None)
        for member, label in event_type_choices():
            self._type_filter.addItem(label, member)
        self._type_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        filter_row.addWidget(self._type_filter)

        filter_row.addWidget(QLabel(t("credit_card_detail.filter_category")))
        self._category_filter = QComboBox()
        self._category_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        filter_row.addWidget(self._category_filter)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("credit_card_detail.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        filter_row.addWidget(self._search)

        btn_search = QPushButton(t("common.search"))
        btn_search.setIcon(icons.icon("fa6s.magnifying-glass"))
        btn_search.clicked.connect(self.refresh)
        filter_row.addWidget(btn_search)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._debt_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("credit_card_detail.current_debt"), self._debt_label))

        self._available_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("credit_card_detail.available_credit"), self._available_label))

        self._limit_label = QLabel(format_currency(0, "BRL"))
        cards_layout.addWidget(make_stat_card(t("credit_card_detail.credit_limit"), self._limit_label))

        layout.addLayout(cards_layout)

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

    def set_card(self, card_id: str):
        """Point the screen at a card and refresh its data."""
        self._card_id = card_id
        self.refresh()

    def has_card(self) -> bool:
        return self._card_id is not None

    def _on_pay_clicked(self):
        if self._card_id is not None:
            self.pay_card_requested.emit(self._card_id)

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
        """+1 for a payment (lowers the card's debt), -1 for a charge."""
        return 1 if event.event_type == EventType.CARD_PAYMENT.value else -1

    def refresh(self):
        if self._card_id is None:
            self._header.setText(t("credit_card_detail.select_prompt"))
            self._table.setRowCount(0)
            return

        self._populate_category_filter()

        categories_map = {c.id: c.name for c in self._category_use_cases.list_categories()}
        counterparties_map = {
            c.id: c.name for c in self._counterparty_use_cases.list_counterparties()
        }

        status = self._card_use_cases.get_status(self._card_id)
        if status:
            self._header.setText(t("credit_card_detail.header", name=status.card.name))
            self._debt_label.setText(format_currency(status.current_debt, "BRL"))
            self._debt_label.setStyleSheet(f"color: {theme.EXPENSE};")
            self._available_label.setText(format_currency(status.available_credit, "BRL"))
            self._available_label.setStyleSheet(
                f"color: {theme.INCOME if status.available_credit >= 0 else theme.EXPENSE};"
            )
            self._limit_label.setText(format_currency(status.card.credit_limit, "BRL"))

        date_from, date_to = self._date_range.resolved_range()
        # The repository treats date_to as an exclusive upper bound, but
        # resolved_range()'s date_to is inclusive of that whole day.
        date_to_exclusive = date_to + timedelta(days=1) if date_to else None

        self._refresh_table(date_from, date_to_exclusive, categories_map, counterparties_map)

    def _refresh_table(self, date_from, date_to_exclusive, categories_map, counterparties_map):
        event_type = self._type_filter.currentData()
        category_id = self._category_filter.currentData()
        description = self._search.text().strip() or None

        events = self._event_use_cases.list_events(
            date_from=date_from,
            date_to=date_to_exclusive,
            event_type=event_type,
            category_id=category_id,
            credit_card_id=self._card_id,
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
            self._populate_row(i, payload, is_virtual, categories_map, counterparties_map)

        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _pending_occurrences(self, date_from, date_to_exclusive, event_type, category_id, description):
        # Pending occurrences project into the future, so an open-ended range
        # (the "All Time" default gives None) must be bounded or generation
        # would never terminate - show pending charges up to today when no
        # explicit upper bound is set, like the Events tab.
        occ_from = date_from or date.min
        occ_to = date_to_exclusive or (date.today() + timedelta(days=1))
        occurrences = self._recurring_event_use_cases.get_pending_occurrences(
            occ_from, occ_to,
            category_id=category_id,
            description=description,
        )
        # get_pending_occurrences filters by account, not card, so keep only the
        # recurrences charged to this card; apply the Type filter here too.
        occurrences = [o for o in occurrences if o.credit_card_id == self._card_id]
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

    def _populate_row(self, i, e, is_virtual, categories_map, counterparties_map):
        type_label = event_type_label(e.event_type)
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
            italic = QFont()
            italic.setItalic(True)
            for col in range(6):
                self._table.item(i, col).setFont(italic)
