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
    def __init__(self, financial_event_repository: FinancialEventRepository,
                 category_repository=None):
        self._financial_event_repository = financial_event_repository
        self._category_repository = category_repository

    def _investment_category_ids(self):
        if self._category_repository is None:
            return set()
        return self._category_repository.find_investment_ids()

    def get_summary(self, year: int, month: int) -> MonthlySummary:
        date_from = date(year, month, 1)
        if month == 12:
            date_to = date(year + 1, 1, 1)
        else:
            date_to = date(year, month + 1, 1)

        events = self._financial_event_repository.find_all(
            date_from=date_from, date_to=date_to
        )

        # Events in an investment-flagged category are excluded (balance-only).
        investment_cats = self._investment_category_ids()
        income = sum(
            e.amount for e in events
            if e.event_type in (EventType.INCOME, EventType.REFUND)
            and e.category_id not in investment_cats
        )
        # Skip credit-card charges whose bill is still open: counting both the
        # charge and its later CARD_PAYMENT would double the spend and make
        # these totals disagree with the account summary ("Resumo de contas").
        expenses = sum(
            e.amount for e in events
            if e.event_type in (
                EventType.EXPENSE, EventType.PURCHASE, EventType.CARD_PAYMENT,
                EventType.LOAN_PAYMENT,
            ) and not e.is_uncleared_card_charge
            and e.category_id not in investment_cats
        )
        net = income - expenses

        return MonthlySummary(
            year=year, month=month, income=income, expenses=expenses, net=net
        )
