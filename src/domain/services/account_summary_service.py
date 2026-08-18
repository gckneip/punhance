from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.account_repository import AccountRepository
from src.domain.entities.financial_event import EventType


@dataclass
class AccountSummaryItem:
    account_id: str
    account_name: str
    account_type: str
    initial_balance: float
    total_income: float
    total_expenses: float
    current_balance: float


@dataclass
class AccountSummary:
    items: List[AccountSummaryItem] = field(default_factory=list)
    total_initial: float = 0.0
    total_income: float = 0.0
    total_expenses: float = 0.0
    grand_total: float = 0.0


class AccountSummaryService:
    def __init__(
        self,
        financial_event_repository: FinancialEventRepository,
        account_repository: AccountRepository,
    ):
        self._event_repo = financial_event_repository
        self._account_repo = account_repository

    def get_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> AccountSummary:
        accounts = self._account_repo.find_all()
        events = self._event_repo.find_all(date_from=date_from, date_to=date_to)

        agg: Dict[str, Dict[str, float]] = {}

        def bucket(acc_id: Optional[str]) -> Dict[str, float]:
            key = acc_id or "__unassigned__"
            if key not in agg:
                agg[key] = {"income": 0.0, "expenses": 0.0}
            return agg[key]

        for e in events:
            if e.event_type == EventType.TRANSFER:
                bucket(e.account_id)["expenses"] += e.amount
                bucket(e.destination_account_id)["income"] += e.amount
            elif e.event_type in (EventType.INCOME, EventType.REFUND):
                bucket(e.account_id)["income"] += e.amount
            elif e.event_type in (
                EventType.EXPENSE, EventType.PURCHASE, EventType.CARD_PAYMENT,
                EventType.LOAN_PAYMENT, EventType.INVESTMENT,
            ):
                bucket(e.account_id)["expenses"] += e.amount

        summary = AccountSummary()
        for acc in accounts:
            a = agg.pop(acc.id, {"income": 0.0, "expenses": 0.0})
            item = AccountSummaryItem(
                account_id=acc.id,
                account_name=acc.name,
                account_type=acc.type.value,
                initial_balance=acc.initial_balance,
                total_income=a["income"],
                total_expenses=a["expenses"],
                current_balance=acc.initial_balance + a["income"] - a["expenses"],
            )
            summary.items.append(item)
            summary.total_initial += acc.initial_balance
            summary.total_income += a["income"]
            summary.total_expenses += a["expenses"]

        # Events referencing no account (or an account not returned above) still
        # count toward the totals so the grand total always matches the raw events.
        unassigned_income = sum(a["income"] for a in agg.values())
        unassigned_expenses = sum(a["expenses"] for a in agg.values())
        if unassigned_income or unassigned_expenses:
            summary.items.append(AccountSummaryItem(
                account_id="__unassigned__",
                account_name="(Sem conta associada)",
                account_type="unassigned",
                initial_balance=0.0,
                total_income=unassigned_income,
                total_expenses=unassigned_expenses,
                current_balance=unassigned_income - unassigned_expenses,
            ))
            summary.total_income += unassigned_income
            summary.total_expenses += unassigned_expenses

        summary.grand_total = (
            summary.total_initial + summary.total_income - summary.total_expenses
        )
        return summary
