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
    # Internal transfers in/out of this account. Kept separate from
    # income/expenses (a transfer between your own accounts is not real
    # income or spending) but still moves the account's balance.
    transfer_in: float = 0.0
    transfer_out: float = 0.0


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
                agg[key] = {
                    "income": 0.0, "expenses": 0.0,
                    "transfer_in": 0.0, "transfer_out": 0.0,
                }
            return agg[key]

        for e in events:
            if e.event_type == EventType.TRANSFER:
                # A transfer moves money between the user's own accounts. It
                # affects each account's balance but is not income or spending,
                # so it is tracked separately and left out of the income/expense
                # totals (which must agree with the dashboard's figures).
                bucket(e.account_id)["transfer_out"] += e.amount
                bucket(e.destination_account_id)["transfer_in"] += e.amount
            elif e.event_type in (EventType.INCOME, EventType.REFUND):
                bucket(e.account_id)["income"] += e.amount
            elif e.event_type == EventType.CARD_PAYMENT:
                bucket(e.account_id)["expenses"] += e.amount
            elif e.event_type in (
                EventType.EXPENSE, EventType.PURCHASE,
                EventType.LOAN_PAYMENT, EventType.INVESTMENT,
            ):
                if e.credit_card_id:
                    # Charged to a credit card, not a bank account - this
                    # isn't a real account outflow yet. It becomes one later,
                    # when the card bill is paid (see CreditCardUseCases.pay_card),
                    # which creates its own CARD_PAYMENT event against a real account.
                    continue
                bucket(e.account_id)["expenses"] += e.amount

        empty = {"income": 0.0, "expenses": 0.0, "transfer_in": 0.0, "transfer_out": 0.0}
        summary = AccountSummary()
        for acc in accounts:
            a = agg.pop(acc.id, empty)
            net_transfer = a["transfer_in"] - a["transfer_out"]
            item = AccountSummaryItem(
                account_id=acc.id,
                account_name=acc.name,
                account_type=acc.type.value,
                initial_balance=acc.initial_balance,
                total_income=a["income"],
                total_expenses=a["expenses"],
                current_balance=acc.initial_balance + a["income"] - a["expenses"] + net_transfer,
                transfer_in=a["transfer_in"],
                transfer_out=a["transfer_out"],
            )
            summary.items.append(item)
            summary.total_initial += acc.initial_balance
            summary.total_income += a["income"]
            summary.total_expenses += a["expenses"]

        # Events referencing no account (or an account not returned above) still
        # count toward the totals so the grand total always matches the raw events.
        unassigned_income = sum(a["income"] for a in agg.values())
        unassigned_expenses = sum(a["expenses"] for a in agg.values())
        unassigned_transfer_in = sum(a["transfer_in"] for a in agg.values())
        unassigned_transfer_out = sum(a["transfer_out"] for a in agg.values())
        unassigned_net_transfer = unassigned_transfer_in - unassigned_transfer_out
        if (unassigned_income or unassigned_expenses
                or unassigned_transfer_in or unassigned_transfer_out):
            summary.items.append(AccountSummaryItem(
                account_id="__unassigned__",
                account_name="(Sem conta associada)",
                account_type="unassigned",
                initial_balance=0.0,
                total_income=unassigned_income,
                total_expenses=unassigned_expenses,
                current_balance=unassigned_income - unassigned_expenses + unassigned_net_transfer,
                transfer_in=unassigned_transfer_in,
                transfer_out=unassigned_transfer_out,
            ))
            summary.total_income += unassigned_income
            summary.total_expenses += unassigned_expenses

        # Transfers net to zero across all accounts, so the grand total is still
        # just initial + income - expenses (income/expenses being transfer-free).
        summary.grand_total = (
            summary.total_initial + summary.total_income - summary.total_expenses
        )
        return summary
