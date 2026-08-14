from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional
from src.domain.repositories.financial_event_repository import FinancialEventRepository
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


class CategoryBreakdownService:
    def __init__(self, financial_event_repository: FinancialEventRepository):
        self._financial_event_repository = financial_event_repository

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

        events = self._financial_event_repository.find_all(
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
        )

        grouped: Dict[Optional[str], CategoryBreakdownItem] = {}
        for e in events:
            cat_id = e.category_id
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
            if e.event_type in (EventType.INCOME, EventType.REFUND):
                item.total_income += e.amount
            elif e.event_type in (
                EventType.EXPENSE, EventType.PURCHASE, EventType.CARD_PAYMENT,
                EventType.LOAN_PAYMENT, EventType.INVESTMENT,
            ):
                item.total_expenses += e.amount
            item.net = item.total_income - item.total_expenses

        breakdown = CategoryBreakdown(year=year, month=month)
        breakdown.items = sorted(
            grouped.values(), key=lambda x: x.total_expenses, reverse=True
        )
        breakdown.total_income = sum(i.total_income for i in breakdown.items)
        breakdown.total_expenses = sum(i.total_expenses for i in breakdown.items)
        return breakdown
