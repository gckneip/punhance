"""Google-Calendar-style Day / Week / Month view over financial entries.

Finance entries are date-only (no time-of-day), so every view renders as an
all-day list rather than an hourly grid:
  * Month - a 7-column day-cell grid with colored chips per day.
  * Week  - 7 day columns, each listing that day's entries.
  * Day   - a single-day detail list.

Data merges three sources for the visible window (upper bound exclusive, as the
repository layer expects): confirmed events, pending recurrence occurrences, and
installment due dates. Entries are interactive; the widget emits signals that
MainWindow connects to its existing edit / confirm / skip handlers.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QToolButton, QButtonGroup, QFrame, QScrollArea, QSizePolicy, QMenu,
    QMessageBox,
)

from src.presentation import theme
from src.presentation import icons

# Day the week starts on (Google's default is Sunday). calendar's constants use
# Monday=0..Sunday=6, matching Python's date.weekday(), so the two are aligned.
FIRSTWEEKDAY = calendar.SUNDAY

# Event types that represent money coming in (shown green).
_INCOME_TYPES = {"income", "refund", "investment"}
# Event types with no clear inflow/outflow direction (shown neutral).
_NEUTRAL_TYPES = {"transfer"}

# How many chips a month-view day cell shows before collapsing to "+N more".
_MAX_MONTH_CHIPS = 3


@dataclass
class CalendarEntry:
    """A single thing shown on the calendar, normalized across all sources."""
    entry_date: date
    kind: str            # "event" | "recurring" | "installment"
    label: str
    amount: float
    currency: str
    color: str
    payload: object      # FinancialEventDTO | VirtualOccurrenceDTO | InstallmentDTO


def _classify_balance(e) -> tuple:
    """(income, expense) a confirmed event contributes to the all-accounts total.

    Mirrors AccountSummaryService: transfers add to both source expense and
    destination income (net zero across all accounts, so returned as 0/0 here);
    income/refund are inflows; expense/purchase/loan/investment are outflows
    unless charged to a credit card (deferred to the card payment); card
    payments are outflows.
    """
    et = e.event_type
    if et in ("income", "refund"):
        return (e.amount, 0.0)
    if et == "card_payment":
        return (0.0, e.amount)
    if et in ("expense", "purchase", "loan_payment", "investment"):
        if getattr(e, "credit_card_id", None):
            return (0.0, 0.0)
        return (0.0, e.amount)
    # transfer (and anything unclassified) nets to zero across all accounts.
    return (0.0, 0.0)


def _event_color(event_type: str) -> str:
    if event_type in _INCOME_TYPES:
        return theme.INCOME
    if event_type in _NEUTRAL_TYPES:
        return theme.TEXT_SECONDARY
    return theme.EXPENSE


class CalendarWidget(QWidget):
    """Calendar screen. See module docstring."""

    edit_event_requested = Signal(str)             # real event id
    confirm_occurrence_requested = Signal(object)  # VirtualOccurrenceDTO
    skip_occurrence_requested = Signal(str, object)  # (recurring_event_id, occurrence_date)

    def __init__(
        self,
        financial_event_use_cases,
        recurring_event_use_cases,
        installment_use_cases,
        category_use_cases,
        account_use_cases,
        account_summary_service,
    ):
        super().__init__()
        self._financial_event_use_cases = financial_event_use_cases
        self._recurring_event_use_cases = recurring_event_use_cases
        self._installment_use_cases = installment_use_cases
        self._category_use_cases = category_use_cases
        self._account_use_cases = account_use_cases
        self._account_summary_service = account_summary_service

        self._current_date: date = date.today()
        self._view_mode: str = "month"  # "day" | "week" | "month"
        self._show_totals: bool = True
        self._categories_map: Dict[str, str] = {}
        self._accounts_map: Dict[str, str] = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI ---
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._btn_prev = QToolButton()
        self._btn_prev.setIcon(icons.icon("fa6s.chevron-left"))
        self._btn_prev.setToolTip("Previous")
        self._btn_prev.clicked.connect(self._go_prev)
        header.addWidget(self._btn_prev)

        self._btn_next = QToolButton()
        self._btn_next.setIcon(icons.icon("fa6s.chevron-right"))
        self._btn_next.setToolTip("Next")
        self._btn_next.clicked.connect(self._go_next)
        header.addWidget(self._btn_next)

        self._btn_today = QPushButton("Today")
        self._btn_today.clicked.connect(self._go_today)
        header.addWidget(self._btn_today)

        self._period_label = QLabel("")
        period_font = QFont()
        period_font.setPointSize(theme.STAT_VALUE_FONT_SIZE)
        period_font.setBold(True)
        self._period_label.setFont(period_font)
        self._period_label.setContentsMargins(8, 0, 0, 0)
        header.addWidget(self._period_label)

        header.addStretch()

        self._btn_totals = QToolButton()
        self._btn_totals.setText(" Totals")
        self._btn_totals.setIcon(icons.icon("fa6s.calculator"))
        self._btn_totals.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._btn_totals.setCheckable(True)
        self._btn_totals.setChecked(self._show_totals)
        self._btn_totals.setToolTip(
            "Show each day's income/expense and the running balance across all accounts"
        )
        self._btn_totals.toggled.connect(self._toggle_totals)
        header.addWidget(self._btn_totals)
        header.addSpacing(12)

        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        for mode, label in (("day", "Day"), ("week", "Week"), ("month", "Month")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(mode == self._view_mode)
            btn.clicked.connect(lambda _checked, m=mode: self._set_view(m))
            self._view_group.addButton(btn)
            header.addWidget(btn)

        layout.addLayout(header)

        # Body container that _render() clears and rebuilds each time.
        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(0)
        layout.addLayout(self._body, 1)

    # ------------------------------------------------------------- actions ---
    def _set_view(self, mode: str):
        self._view_mode = mode
        for btn in self._view_group.buttons():
            btn.setChecked(btn.text().lower() == mode)
        self.refresh()

    def _toggle_totals(self, checked: bool):
        self._show_totals = checked
        self.refresh()

    def _go_today(self):
        self._current_date = date.today()
        self.refresh()

    def _go_prev(self):
        self._current_date = self._shift(self._current_date, -1)
        self.refresh()

    def _go_next(self):
        self._current_date = self._shift(self._current_date, +1)
        self.refresh()

    def _shift(self, anchor: date, direction: int) -> date:
        if self._view_mode == "day":
            return anchor + timedelta(days=direction)
        if self._view_mode == "week":
            return anchor + timedelta(days=7 * direction)
        return _add_months(anchor, direction)

    def _open_day(self, day: date):
        self._current_date = day
        self._set_view("day")

    # --------------------------------------------------------------- data ---
    def refresh(self):
        """Reload the visible window and rebuild the current view."""
        self._categories_map = {c.id: c.name for c in self._category_use_cases.list_categories()}
        self._accounts_map = {a.id: a.name for a in self._account_use_cases.list_accounts()}

        _clear_layout(self._body)
        if self._view_mode == "day":
            self._render_day()
        elif self._view_mode == "week":
            self._render_week()
        else:
            self._render_month()

    def _load_entries(self, date_from: date, date_to: date) -> Dict[date, List[CalendarEntry]]:
        """Merge all sources for [date_from, date_to) and bucket by date."""
        buckets: Dict[date, List[CalendarEntry]] = {}

        def add(entry: CalendarEntry):
            buckets.setdefault(entry.entry_date, []).append(entry)

        for e in self._financial_event_use_cases.list_events(date_from=date_from, date_to=date_to):
            add(CalendarEntry(
                entry_date=e.event_date, kind="event", label=e.description,
                amount=e.amount, currency=e.currency, color=_event_color(e.event_type),
                payload=e,
            ))

        for o in self._recurring_event_use_cases.get_pending_occurrences(date_from, date_to):
            add(CalendarEntry(
                entry_date=o.occurrence_date, kind="recurring",
                label=f"{o.description} (recurring)", amount=o.amount, currency=o.currency,
                color=_event_color(o.event_type), payload=o,
            ))

        for inst in self._installment_use_cases.list_installments(date_from=date_from, date_to=date_to):
            add(CalendarEntry(
                entry_date=inst.due_date, kind="installment",
                label=f"Installment #{inst.installment_number}", amount=inst.amount,
                currency="R$", color=theme.PRIMARY, payload=inst,
            ))

        for day_entries in buckets.values():
            day_entries.sort(key=lambda en: (en.kind, en.label))
        return buckets

    def _compute_daily_balances(self, date_from: date, date_to: date):
        """Per-day (income, expense) and the running all-accounts balance.

        Past/present days use confirmed events only. Future days additionally
        fold in pending recurring occurrences, so the balance becomes a
        forward projection. Bucketing mirrors AccountSummaryService exactly so
        the running balance reconciles with income - expense: transfers net to
        zero across all accounts, and credit-card purchases don't hit a bank
        account until the later card payment. The seed is the authoritative
        total across all accounts (incl. each account's initial balance) as of
        the day before the visible window; when that window starts in the
        future, the projection between today and the window start is added to
        the seed so navigating months stays continuous.
        """
        today = date.today()
        projection_start = today + timedelta(days=1)  # occurrences strictly after today

        totals: Dict[date, List[float]] = {}

        def add(day: date, income: float, expense: float):
            bucket = totals.setdefault(day, [0.0, 0.0])
            bucket[0] += income
            bucket[1] += expense

        for e in self._financial_event_use_cases.list_events(date_from=date_from, date_to=date_to):
            add(e.event_date, *_classify_balance(e))

        # Projected recurring occurrences that fall on future days in the window.
        proj_from = max(date_from, projection_start)
        if proj_from < date_to:
            for o in self._recurring_event_use_cases.get_pending_occurrences(proj_from, date_to):
                add(o.occurrence_date, *_classify_balance(o))

        running = self._account_summary_service.get_summary(date_to=date_from).grand_total
        # Fold in future occurrences between today and a future window's start.
        if date_from > projection_start:
            for o in self._recurring_event_use_cases.get_pending_occurrences(projection_start, date_from):
                income, expense = _classify_balance(o)
                running += income - expense

        day_totals: Dict[date, tuple] = {}
        balances: Dict[date, float] = {}
        day = date_from
        while day < date_to:
            income, expense = totals.get(day, (0.0, 0.0))
            running += income - expense
            day_totals[day] = (income, expense)
            balances[day] = running
            day += timedelta(days=1)
        return day_totals, balances

    # ------------------------------------------------------------- render ---
    def _render_month(self):
        year, month = self._current_date.year, self._current_date.month
        weeks = calendar.Calendar(FIRSTWEEKDAY).monthdatescalendar(year, month)
        date_from = weeks[0][0]
        date_to = weeks[-1][-1] + timedelta(days=1)  # exclusive
        buckets = self._load_entries(date_from, date_to)
        if self._show_totals:
            day_totals, balances = self._compute_daily_balances(date_from, date_to)
        else:
            day_totals, balances = {}, {}

        self._period_label.setText(self._current_date.strftime("%B %Y"))

        grid = QGridLayout()
        grid.setSpacing(4)
        for col, wd in enumerate(_weekday_order()):
            lbl = QLabel(calendar.day_abbr[wd])
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        today = date.today()
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                income, expense = day_totals.get(day, (0.0, 0.0))
                cell = self._make_month_cell(
                    day, buckets.get(day, []),
                    in_month=(day.month == month), is_today=(day == today),
                    income=income, expense=expense, balance=balances.get(day, 0.0),
                    show_totals=self._show_totals, is_future=(day > today),
                )
                grid.addWidget(cell, row, col)

        for col in range(7):
            grid.setColumnStretch(col, 1)
        for row in range(1, len(weeks) + 1):
            grid.setRowStretch(row, 1)

        container = QWidget()
        container.setLayout(grid)
        self._body.addWidget(container)

    def _make_month_cell(self, day: date, entries: List[CalendarEntry],
                         in_month: bool, is_today: bool,
                         income: float, expense: float, balance: float,
                         show_totals: bool, is_future: bool) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        bg = theme.SURFACE if in_month else theme.BG_APP
        border = theme.PRIMARY if is_today else theme.BORDER
        border_w = 2 if is_today else 1
        frame.setStyleSheet(
            f"QFrame {{ background: {bg}; border: {border_w}px solid {border};"
            f" border-radius: 6px; }}"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(2)

        num = QLabel(str(day.day))
        num_color = theme.TEXT_PRIMARY if in_month else theme.TEXT_SECONDARY
        num.setStyleSheet(
            f"color: {theme.PRIMARY if is_today else num_color}; border: none;"
            f" {'font-weight: bold;' if is_today else ''}"
        )
        v.addWidget(num)

        for entry in entries[:_MAX_MONTH_CHIPS]:
            v.addWidget(self._make_chip(entry, compact=True))

        overflow = len(entries) - _MAX_MONTH_CHIPS
        if overflow > 0:
            more = QToolButton()
            more.setText(f"+{overflow} more")
            more.setStyleSheet(
                f"QToolButton {{ border: none; color: {theme.TEXT_SECONDARY};"
                f" font-size: {theme.SMALL_FONT_SIZE}pt; text-align: left; }}"
            )
            more.clicked.connect(lambda _=False, d=day: self._open_day(d))
            v.addWidget(more)

        v.addStretch()
        if show_totals:
            v.addWidget(self._make_cell_footer(income, expense, balance, in_month, is_future))
        return frame

    def _make_cell_footer(self, income: float, expense: float,
                          balance: float, in_month: bool, is_future: bool) -> QWidget:
        """Compact per-day summary pinned to the bottom of a month cell:
        an income/expense line (only when non-zero) and the running balance.

        Future days are a projection (they fold in pending recurring
        occurrences), so their figures are rendered in italic to distinguish
        them from confirmed actuals."""
        box = QWidget()
        # Ignored width: the footer fills the cell but never widens it, so the
        # month grid's minimum width stays independent of the numbers shown.
        box.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 3, 0, 0)
        outer.setSpacing(1)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {theme.BORDER}; border: none;")
        outer.addWidget(sep)

        dim = "" if in_month else "opacity: 0.6;"
        proj = "font-style: italic;" if is_future else ""
        small = f"font-size: {theme.SMALL_FONT_SIZE}pt; border: none;"
        proj_word = "Projected " if is_future else ""

        if income or expense:
            flow = QHBoxLayout()
            flow.setContentsMargins(0, 0, 0, 0)
            flow.setSpacing(4)
            if income:
                inc = QLabel(f"+{income:,.0f}")
                inc.setToolTip(f"{proj_word}income: R$ {income:,.2f}")
                inc.setStyleSheet(f"color: {theme.INCOME}; {small} {dim} {proj}")
                flow.addWidget(inc)
            flow.addStretch()
            if expense:
                exp = QLabel(f"-{expense:,.0f}")
                exp.setToolTip(f"{proj_word}expenses: R$ {expense:,.2f}")
                exp.setStyleSheet(f"color: {theme.EXPENSE}; {small} {dim} {proj}")
                flow.addWidget(exp)
            outer.addLayout(flow)

        bal = QLabel(f"R$ {balance:,.0f}")
        bal.setToolTip(f"{proj_word}total across all accounts: R$ {balance:,.2f}")
        bal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bal_color = theme.TEXT_PRIMARY if balance >= 0 else theme.EXPENSE
        bal.setStyleSheet(f"color: {bal_color}; {small} font-weight: bold; {dim} {proj}")
        outer.addWidget(bal)
        return box

    def _render_week(self):
        week_start = _week_start(self._current_date)
        days = [week_start + timedelta(days=i) for i in range(7)]
        buckets = self._load_entries(week_start, week_start + timedelta(days=7))

        end = days[-1]
        if week_start.year == end.year:
            self._period_label.setText(
                f"{week_start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
            )
        else:
            self._period_label.setText(
                f"{week_start.strftime('%b %d, %Y')} - {end.strftime('%b %d, %Y')}"
            )

        columns = QHBoxLayout()
        columns.setSpacing(6)
        today = date.today()
        for day in days:
            columns.addWidget(self._make_week_column(day, buckets.get(day, []), day == today), 1)

        container = QWidget()
        container.setLayout(columns)
        self._body.addWidget(container)

    def _make_week_column(self, day: date, entries: List[CalendarEntry], is_today: bool) -> QWidget:
        col = QFrame()
        border = theme.PRIMARY if is_today else theme.BORDER
        col.setStyleSheet(
            f"QFrame {{ background: {theme.SURFACE}; border: {2 if is_today else 1}px solid {border};"
            f" border-radius: 6px; }}"
        )
        v = QVBoxLayout(col)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)

        head = QLabel(f"{calendar.day_abbr[day.weekday()]} {day.day}")
        head.setAlignment(Qt.AlignCenter)
        head.setStyleSheet(
            f"color: {theme.PRIMARY if is_today else theme.TEXT_PRIMARY}; border: none;"
            f" font-weight: bold;"
        )
        v.addWidget(head)

        scroll_body = QVBoxLayout()
        scroll_body.setSpacing(4)
        for entry in entries:
            scroll_body.addWidget(self._make_chip(entry, compact=False))
        scroll_body.addStretch()

        inner = QWidget()
        inner.setLayout(scroll_body)
        inner.setStyleSheet("border: none;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)
        return col

    def _render_day(self):
        day = self._current_date
        buckets = self._load_entries(day, day + timedelta(days=1))
        entries = buckets.get(day, [])

        self._period_label.setText(day.strftime("%A, %b %d, %Y"))

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(6)

        if not entries:
            empty = QLabel("Nothing scheduled.")
            empty.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
            body.addWidget(empty)
        else:
            for entry in entries:
                body.addWidget(self._make_day_row(entry))
        body.addStretch()

        inner = QWidget()
        inner.setLayout(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        self._body.addWidget(scroll)

    def _make_day_row(self, entry: CalendarEntry) -> QWidget:
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER};"
            f" border-left: 4px solid {entry.color}; border-radius: 6px; }}"
        )
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(8)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        title = QLabel(entry.label)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setItalic(entry.kind == "recurring")
        title.setFont(title_font)
        title.setStyleSheet("border: none;")
        title.setWordWrap(True)  # wrap long descriptions instead of forcing width
        text_box.addWidget(title)

        subtitle = self._entry_context(entry)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(
                f"color: {theme.TEXT_SECONDARY}; border: none;"
                f" font-size: {theme.SMALL_FONT_SIZE}pt;"
            )
            text_box.addWidget(sub)
        h.addLayout(text_box, 1)

        amount = QLabel(f"{entry.currency} {entry.amount:.2f}")
        amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amt_font = QFont()
        amt_font.setBold(True)
        amount.setFont(amt_font)
        amount.setStyleSheet(f"color: {entry.color}; border: none;")
        h.addWidget(amount)

        edit = QToolButton()
        edit.setIcon(icons.icon("fa6s.ellipsis-vertical"))
        edit.setStyleSheet("QToolButton { border: none; }")
        edit.setToolTip("Actions")
        edit.clicked.connect(lambda _=False, e=entry: self._on_entry_clicked(e))
        h.addWidget(edit)

        # Make the whole row clickable too.
        row.mousePressEvent = lambda _event, e=entry: self._on_entry_clicked(e)
        row.setCursor(Qt.PointingHandCursor)
        return row

    def _entry_context(self, entry: CalendarEntry) -> str:
        payload = entry.payload
        if entry.kind == "installment":
            return f"Status: {payload.status}"
        parts = []
        cat = self._categories_map.get(getattr(payload, "category_id", None))
        acc = self._accounts_map.get(getattr(payload, "account_id", None))
        if cat:
            parts.append(cat)
        if acc:
            parts.append(acc)
        return "  ·  ".join(parts)

    # --------------------------------------------------------------- chip ---
    def _make_chip(self, entry: CalendarEntry, compact: bool) -> QToolButton:
        btn = QToolButton()
        text = entry.label if compact else f"{entry.label}  {entry.currency} {entry.amount:.2f}"
        btn.setText(text)
        btn.setToolTip(f"{entry.label}\n{entry.currency} {entry.amount:.2f}")
        btn.setCursor(Qt.PointingHandCursor)
        # Ignored (not Expanding) so a long label never dictates the cell/column
        # width — the chip fills whatever width the cell gives it and clips,
        # with the full text still available via the tooltip.
        btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setMinimumWidth(0)
        tint = _tint(entry.color)
        italic = "font-style: italic;" if entry.kind == "recurring" else ""
        btn.setStyleSheet(
            f"QToolButton {{ background: {tint}; color: {entry.color};"
            f" border: none; border-left: 3px solid {entry.color};"
            f" border-radius: 4px; padding: 2px 4px; text-align: left;"
            f" font-size: {theme.SMALL_FONT_SIZE}pt; {italic} }}"
            f"QToolButton:hover {{ background: {theme.SELECTION}; }}"
        )
        btn.clicked.connect(lambda _=False, e=entry: self._on_entry_clicked(e))
        return btn

    # ------------------------------------------------------------ dispatch ---
    def _on_entry_clicked(self, entry: CalendarEntry):
        if entry.kind == "event":
            self.edit_event_requested.emit(entry.payload.id)
        elif entry.kind == "recurring":
            self._show_recurring_menu(entry.payload)
        elif entry.kind == "installment":
            self._show_installment_detail(entry.payload)

    def _show_recurring_menu(self, occ):
        menu = QMenu(self)
        menu.addAction(icons.icon("fa6s.check"), "Confirm",
                       lambda: self.confirm_occurrence_requested.emit(occ))
        menu.addAction(icons.icon("fa6s.forward-step"), "Skip",
                       lambda: self.skip_occurrence_requested.emit(
                           occ.recurring_event_id, occ.occurrence_date))
        menu.exec(_cursor_pos())

    def _show_installment_detail(self, inst):
        QMessageBox.information(
            self, "Installment",
            f"Installment #{inst.installment_number}\n"
            f"Due: {inst.due_date.isoformat()}\n"
            f"Amount: R$ {inst.amount:.2f}\n"
            f"Status: {inst.status}\n"
            f"Plan: {inst.installment_plan_id}",
        )


# --------------------------------------------------------------- helpers ---
def _weekday_order() -> List[int]:
    """Weekday indices (Mon=0..Sun=6) in display order from FIRSTWEEKDAY."""
    return [(FIRSTWEEKDAY + i) % 7 for i in range(7)]


def _week_start(anchor: date) -> date:
    return anchor - timedelta(days=(anchor.weekday() - FIRSTWEEKDAY) % 7)


def _add_months(anchor: date, months: int) -> date:
    """Shift by whole months, clamping the day to the target month's length."""
    total = anchor.month - 1 + months
    year = anchor.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(anchor.day, last_day))


def _tint(color: str) -> str:
    """A pale translucent version of a hex color for chip backgrounds."""
    color = color.lstrip("#")
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, 0.14)"


def _cursor_pos():
    from PySide6.QtGui import QCursor
    return QCursor.pos()


def _clear_layout(layout):
    """Recursively remove and delete every item in a layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        else:
            child = item.layout()
            if child is not None:
                _clear_layout(child)
                child.deleteLater()
