from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.purchase_repository import PurchaseRepository
from src.domain.entities.financial_event import EventType


@dataclass
class CategoryBreakdownItem:
    category_id: Optional[str]
    total_income: float
    total_expenses: float
    net: float
    event_count: int


@dataclass
class CategoryBreakdown:
    year: int
    month: int
    items: List[CategoryBreakdownItem] = field(default_factory=list)
    total_income: float = 0.0
    total_expenses: float = 0.0


@dataclass
class CategoryEventRow:
    """A single event contributing to a category, for the drill-down modal."""
    event_date: date
    description: str
    event_type: EventType
    amount: float
    currency: str
    is_income: bool


class CategoryBreakdownService:
    def __init__(
        self,
        financial_event_repository: FinancialEventRepository,
        purchase_repository: Optional[PurchaseRepository] = None,
        category_repository=None,
    ):
        self._financial_event_repository = financial_event_repository
        self._purchase_repository = purchase_repository
        self._category_repository = category_repository

    def _investment_category_ids(self):
        if self._category_repository is None:
            return set()
        return self._category_repository.find_investment_ids()

    def get_breakdown(
        self,
        year: int,
        month: int,
        category_id: Optional[str] = None,
    ) -> CategoryBreakdown:
        date_from = date(year, month, 1)
        if month == 12:
            date_to = date(year + 1, 1, 1)
        else:
            date_to = date(year, month + 1, 1)
        return self._breakdown_for_range(date_from, date_to, category_id, year=year, month=month)

    def get_breakdown_for_range(
        self,
        date_from: date,
        date_to: date,
        category_id: Optional[str] = None,
    ) -> CategoryBreakdown:
        """Like get_breakdown, but for an arbitrary [date_from, date_to)
        range instead of a single calendar month."""
        return self._breakdown_for_range(date_from, date_to, category_id)

    def _breakdown_for_range(
        self,
        date_from: date,
        date_to: date,
        category_id: Optional[str],
        year: int = 0,
        month: int = 0,
    ) -> CategoryBreakdown:
        events = self._financial_event_repository.find_all(
            date_from=date_from,
            date_to=date_to,
        )

        grouped: Dict[Optional[str], CategoryBreakdownItem] = {}
        investment_cats = self._investment_category_ids()

        def add(cat_id: Optional[str], event_type: EventType, amount: float) -> None:
            if cat_id in investment_cats:
                return  # investment-flagged categories are excluded from the breakdown
            if cat_id not in grouped:
                grouped[cat_id] = CategoryBreakdownItem(
                    category_id=cat_id,
                    total_income=0.0,
                    total_expenses=0.0,
                    net=0.0,
                    event_count=0,
                )
            item = grouped[cat_id]
            item.event_count += 1
            if event_type in (EventType.INCOME, EventType.REFUND):
                item.total_income += amount
            elif event_type in (
                # CARD_PAYMENT/TRANSFER/INVESTMENT/REDEMPTION are filtered out
                # before reaching here.
                EventType.EXPENSE, EventType.PURCHASE,
                EventType.LOAN_PAYMENT,
            ):
                item.total_expenses += amount
            item.net = item.total_income - item.total_expenses

        for e in events:
            # Skip events that carry no category and would distort the picture:
            #  - TRANSFER: internal money movement between the user's own
            #    accounts, not income or spending.
            #  - CARD_PAYMENT: paying a credit-card bill. The spending it settles
            #    is already recorded (with real categories) by the individual
            #    card purchases, so counting it here double-counts and dumps an
            #    uncategorized lump into the "no category" slice.
            if e.event_type in (
                EventType.TRANSFER, EventType.CARD_PAYMENT,
                EventType.INVESTMENT, EventType.REDEMPTION,
            ):
                continue

            items = []
            if e.event_type == EventType.PURCHASE and self._purchase_repository is not None:
                purchase = self._purchase_repository.find_by_financial_event(e.id)
                if purchase is not None:
                    items = self._purchase_repository.find_items_by_purchase(purchase.id)

            if items:
                # Split the purchase across each item's own category instead of
                # the event's single (often None, when items span categories) one.
                for purchase_item in items:
                    add(purchase_item.category_id, e.event_type, purchase_item.total_price)
            else:
                add(e.category_id, e.event_type, e.amount)

        breakdown_items = list(grouped.values())
        if category_id is not None:
            breakdown_items = [i for i in breakdown_items if i.category_id == category_id]

        breakdown = CategoryBreakdown(year=year, month=month)
        breakdown.items = sorted(
            breakdown_items, key=lambda x: x.total_expenses, reverse=True
        )
        breakdown.total_income = sum(i.total_income for i in breakdown.items)
        breakdown.total_expenses = sum(i.total_expenses for i in breakdown.items)
        return breakdown

    def get_events_for_category(
        self,
        date_from: date,
        date_to: date,
        category_id: Optional[str],
    ) -> List[CategoryEventRow]:
        """Individual events that contribute to a single category over
        [date_from, date_to), for the category drill-down modal.

        Mirrors the exclusion and purchase-item-splitting rules of
        :meth:`_breakdown_for_range` so the modal's rows reconcile with the
        totals shown for the category. ``category_id=None`` selects the
        "unassigned" bucket.
        """
        events = self._financial_event_repository.find_all(
            date_from=date_from,
            date_to=date_to,
        )

        rows: List[CategoryEventRow] = []
        for e in events:
            if e.event_type in (
                EventType.TRANSFER, EventType.CARD_PAYMENT,
                EventType.INVESTMENT, EventType.REDEMPTION,
            ):
                continue

            is_income = e.event_type in (EventType.INCOME, EventType.REFUND)

            items = []
            if e.event_type == EventType.PURCHASE and self._purchase_repository is not None:
                purchase = self._purchase_repository.find_by_financial_event(e.id)
                if purchase is not None:
                    items = self._purchase_repository.find_items_by_purchase(purchase.id)

            if items:
                # A purchase is split across its items' categories; sum the part
                # that lands in the requested category (one row per event).
                matched = [it for it in items if it.category_id == category_id]
                if not matched:
                    continue
                amount = sum(it.total_price for it in matched)
                rows.append(CategoryEventRow(
                    e.event_date, e.description, e.event_type, amount, e.currency, is_income,
                ))
            elif e.category_id == category_id:
                rows.append(CategoryEventRow(
                    e.event_date, e.description, e.event_type, e.amount, e.currency, is_income,
                ))

        rows.sort(key=lambda r: r.event_date, reverse=True)
        return rows
