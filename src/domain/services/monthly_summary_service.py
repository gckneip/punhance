from dataclasses import dataclass
from datetime import date
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.entities.financial_event import EventType


@dataclass
class MonthlySummary:
    year: int
    month: int
    income: float
    expenses: float
    net: float


class MonthlySummaryService:
    def __init__(self, financial_event_repository: FinancialEventRepository):
        self._financial_event_repository = financial_event_repository

    def get_summary(self, year: int, month: int) -> MonthlySummary:
        date_from = date(year, month, 1)
        if month == 12:
            date_to = date(year + 1, 1, 1)
        else:
            date_to = date(year, month + 1, 1)

        events = self._financial_event_repository.find_all(
            date_from=date_from, date_to=date_to
        )

        income = sum(
            e.amount for e in events if e.event_type in (EventType.INCOME, EventType.REFUND)
        )
        expenses = sum(
            e.amount for e in events if e.event_type in (
                EventType.EXPENSE, EventType.PURCHASE, EventType.CARD_PAYMENT,
                EventType.LOAN_PAYMENT, EventType.INVESTMENT,
            )
        )
        net = income - expenses

        return MonthlySummary(
            year=year, month=month, income=income, expenses=expenses, net=net
        )
