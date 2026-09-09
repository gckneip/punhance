from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.domain.entities.financial_event import EventType
from src.domain.entities.installment import InstallmentStatus
from src.domain.repositories.account_repository import AccountRepository
from src.domain.repositories.category_repository import CategoryRepository
from src.domain.repositories.counterparty_repository import CounterpartyRepository
from src.domain.repositories.credit_card_repository import CreditCardRepository
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.installment_plan_repository import InstallmentPlanRepository
from src.domain.repositories.installment_repository import InstallmentRepository
from src.domain.repositories.purchase_repository import PurchaseRepository
from src.domain.repositories.recurring_event_repository import RecurringEventRepository
from src.domain.services.account_summary_service import AccountSummaryService
from src.domain.services.category_breakdown_service import CategoryBreakdownService
from src.domain.services.credit_card_service import CreditCardService
from src.domain.services.monthly_summary_service import MonthlySummaryService
from src.domain.services.recurring_event_service import RecurringEventService

INCOME_TYPES = (EventType.INCOME, EventType.REFUND)
EXPENSE_TYPES = (
    EventType.EXPENSE, EventType.PURCHASE, EventType.CARD_PAYMENT,
    EventType.LOAN_PAYMENT, EventType.INVESTMENT,
)


class MetricType(Enum):
    INCOME = "income"
    EXPENSES = "expenses"
    NET = "net"
    BALANCE = "balance"
    CREDIT_CARD_DEBT = "credit_card_debt"
    INSTALLMENT_DUE = "installment_due"


class GroupByDimension(Enum):
    NONE = "none"
    MONTH = "month"
    CATEGORY = "category"
    ACCOUNT = "account"
    COUNTERPARTY = "counterparty"
    CREDIT_CARD = "credit_card"


class ChartType(Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    TABLE = "table"
    STAT = "stat"


# Which GroupByDimension values are meaningful for each metric. MONTH means
# "use get_time_series instead of get_breakdown" - callers should route on it
# before calling either method.
VALID_GROUP_BYS: Dict[MetricType, Tuple[GroupByDimension, ...]] = {
    MetricType.INCOME: (
        GroupByDimension.NONE, GroupByDimension.MONTH, GroupByDimension.CATEGORY,
        GroupByDimension.ACCOUNT, GroupByDimension.COUNTERPARTY,
    ),
    MetricType.EXPENSES: (
        GroupByDimension.NONE, GroupByDimension.MONTH, GroupByDimension.CATEGORY,
        GroupByDimension.ACCOUNT, GroupByDimension.COUNTERPARTY,
    ),
    MetricType.NET: (
        GroupByDimension.NONE, GroupByDimension.MONTH, GroupByDimension.CATEGORY,
        GroupByDimension.ACCOUNT, GroupByDimension.COUNTERPARTY,
    ),
    MetricType.BALANCE: (GroupByDimension.NONE, GroupByDimension.MONTH, GroupByDimension.ACCOUNT),
    MetricType.CREDIT_CARD_DEBT: (GroupByDimension.NONE, GroupByDimension.CREDIT_CARD),
    MetricType.INSTALLMENT_DUE: (GroupByDimension.NONE, GroupByDimension.MONTH),
}


def validate_metric_group_by(metric: MetricType, group_by: GroupByDimension) -> None:
    allowed = VALID_GROUP_BYS.get(metric, ())
    if group_by not in allowed:
        raise ValueError(f"{metric.value} cannot be grouped by {group_by.value}")


@dataclass
class DateRangeSpec:
    mode: str  # "fixed" | "rolling" | "calendar"
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    unit: Optional[str] = None  # rolling: "days" | "months"
    amount: Optional[int] = None  # rolling: N
    period: Optional[str] = None  # calendar: "month" | "year"
    offset: int = 0  # calendar: 0=current, -1=previous, ...

    @classmethod
    def from_dict(cls, d: dict) -> "DateRangeSpec":
        d = dict(d)
        if d.get("date_from"):
            d["date_from"] = date.fromisoformat(d["date_from"])
        if d.get("date_to"):
            d["date_to"] = date.fromisoformat(d["date_to"])
        return cls(**d)


@dataclass
class ChartFilters:
    account_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    counterparty_ids: Optional[List[str]] = None
    credit_card_ids: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "ChartFilters":
        d = d or {}
        return cls(
            account_ids=d.get("account_ids") or None,
            category_ids=d.get("category_ids") or None,
            counterparty_ids=d.get("counterparty_ids") or None,
            credit_card_ids=d.get("credit_card_ids") or None,
        )


@dataclass
class TimeSeriesResult:
    labels: List[str] = field(default_factory=list)
    series: Dict[str, List[float]] = field(default_factory=dict)


@dataclass
class BreakdownRow:
    dimension_id: Optional[str]
    dimension_label: str
    values: Dict[str, float] = field(default_factory=dict)


@dataclass
class BreakdownResult:
    rows: List[BreakdownRow] = field(default_factory=list)


@dataclass
class UpcomingInstallmentRow:
    due_date: date
    description: str
    amount: float
    installment_number: int
    installment_count: int
    event_id: str


@dataclass
class UpcomingRecurringOccurrenceRow:
    occurrence_date: date
    description: str
    amount: float
    recurring_event_id: str
    frequency_label: str


@dataclass
class CreditCardUtilizationRow:
    credit_card_id: str
    credit_card_name: str
    current_debt: float
    credit_limit: float
    available_credit: float


def _add_one_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _shift_months(d: date, delta: int) -> date:
    month_index = d.month - 1 + delta
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _month_range(date_from: date, date_to: date):
    cursor = date(date_from.year, date_from.month, 1)
    while cursor < date_to:
        yield (cursor.year, cursor.month)
        cursor = _add_one_month(cursor)


_FREQUENCY_SINGULAR = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}


def _frequency_label(rule) -> str:
    unit = rule.frequency.value
    if rule.interval == 1:
        return unit.capitalize()
    return f"Every {rule.interval} {_FREQUENCY_SINGULAR[unit]}s"


class ChartDataService:
    def __init__(
        self,
        financial_event_repository: FinancialEventRepository,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        counterparty_repository: CounterpartyRepository,
        credit_card_repository: CreditCardRepository,
        installment_repository: InstallmentRepository,
        installment_plan_repository: InstallmentPlanRepository,
        purchase_repository: PurchaseRepository,
        recurring_event_repository: RecurringEventRepository,
        monthly_summary_service: MonthlySummaryService,
        category_breakdown_service: CategoryBreakdownService,
        account_summary_service: AccountSummaryService,
        credit_card_service: CreditCardService,
        recurring_event_service: RecurringEventService,
    ):
        self._financial_event_repository = financial_event_repository
        self._account_repository = account_repository
        self._category_repository = category_repository
        self._counterparty_repository = counterparty_repository
        self._credit_card_repository = credit_card_repository
        self._installment_repository = installment_repository
        self._installment_plan_repository = installment_plan_repository
        self._purchase_repository = purchase_repository
        self._recurring_event_repository = recurring_event_repository
        self._monthly_summary_service = monthly_summary_service
        self._category_breakdown_service = category_breakdown_service
        self._account_summary_service = account_summary_service
        self._credit_card_service = credit_card_service
        self._recurring_event_service = recurring_event_service

    def resolve_date_range(
        self, spec: DateRangeSpec, today: Optional[date] = None
    ) -> Tuple[Optional[date], Optional[date]]:
        today = today or date.today()

        if spec.mode == "fixed":
            date_to = spec.date_to + timedelta(days=1) if spec.date_to else None
            return spec.date_from, date_to

        if spec.mode == "rolling":
            amount = spec.amount or 1
            if spec.unit == "days":
                return today - timedelta(days=amount), today + timedelta(days=1)
            if spec.unit == "months":
                month_to = _add_one_month(date(today.year, today.month, 1))
                month_from = _shift_months(date(today.year, today.month, 1), -(amount - 1))
                return month_from, month_to
            raise ValueError(f"Unknown rolling unit: {spec.unit}")

        if spec.mode == "calendar":
            if spec.period == "month":
                target = _shift_months(date(today.year, today.month, 1), spec.offset)
                return target, _add_one_month(target)
            if spec.period == "year":
                target_year = today.year + spec.offset
                return date(target_year, 1, 1), date(target_year + 1, 1, 1)
            raise ValueError(f"Unknown calendar period: {spec.period}")

        raise ValueError(f"Unknown date range mode: {spec.mode}")

    def get_time_series(
        self,
        metrics: List[MetricType],
        date_range: DateRangeSpec,
        filters: Optional[ChartFilters] = None,
    ) -> TimeSeriesResult:
        date_from, date_to = self.resolve_date_range(date_range)
        months = list(_month_range(date_from, date_to))
        labels = [f"{y:04d}-{m:02d}" for y, m in months]
        series: Dict[str, List[float]] = {metric.value: [] for metric in metrics}

        running_balance = None
        if MetricType.BALANCE in metrics:
            accounts = self._account_repository.find_all()
            if filters and filters.account_ids:
                accounts = [a for a in accounts if a.id in filters.account_ids]
            running_balance = sum(a.initial_balance for a in accounts)

        needs_income_expense = any(
            m in (MetricType.INCOME, MetricType.EXPENSES, MetricType.NET, MetricType.BALANCE)
            for m in metrics
        )

        for year, month in months:
            income = expenses = 0.0
            if needs_income_expense:
                if filters is None:
                    # No filters: reuse the existing monthly summary aggregation as-is.
                    summary = self._monthly_summary_service.get_summary(year, month)
                    income, expenses = summary.income, summary.expenses
                else:
                    month_from = date(year, month, 1)
                    month_to = _add_one_month(month_from)
                    events = self._events_in_range(month_from, month_to, filters)
                    income, expenses = self._classify(events)

            for metric in metrics:
                if metric == MetricType.INCOME:
                    series[metric.value].append(income)
                elif metric == MetricType.EXPENSES:
                    series[metric.value].append(expenses)
                elif metric == MetricType.NET:
                    series[metric.value].append(income - expenses)
                elif metric == MetricType.BALANCE:
                    running_balance += income - expenses
                    series[metric.value].append(running_balance)
                elif metric == MetricType.INSTALLMENT_DUE:
                    month_from = date(year, month, 1)
                    month_to = _add_one_month(month_from)
                    installments = self._installment_repository.find_all(
                        date_from=month_from, date_to=month_to
                    )
                    series[metric.value].append(sum(i.amount for i in installments))
                else:
                    raise ValueError(f"{metric.value} is not supported in a time series")

        return TimeSeriesResult(labels=labels, series=series)

    def get_breakdown(
        self,
        metrics: List[MetricType],
        group_by: GroupByDimension,
        date_range: DateRangeSpec,
        filters: Optional[ChartFilters] = None,
    ) -> BreakdownResult:
        for metric in metrics:
            validate_metric_group_by(metric, group_by)

        if group_by == GroupByDimension.MONTH:
            raise ValueError("Use get_time_series for MONTH grouping")
        if group_by == GroupByDimension.CATEGORY:
            return self._breakdown_by_category(metrics, date_range, filters)
        if group_by == GroupByDimension.ACCOUNT:
            return self._breakdown_by_account(metrics, date_range, filters)
        if group_by == GroupByDimension.COUNTERPARTY:
            return self._breakdown_by_counterparty(metrics, date_range, filters)
        if group_by == GroupByDimension.CREDIT_CARD:
            return self._breakdown_credit_card_debt(filters)
        if group_by == GroupByDimension.NONE:
            return self._breakdown_none(metrics, date_range, filters)
        raise ValueError(f"Unsupported group_by: {group_by}")

    def get_stat(
        self,
        metric: MetricType,
        date_range: DateRangeSpec,
        filters: Optional[ChartFilters] = None,
    ) -> float:
        result = self.get_breakdown([metric], GroupByDimension.NONE, date_range, filters)
        if not result.rows:
            return 0.0
        return result.rows[0].values.get(metric.value, 0.0)

    def get_upcoming_installments(
        self, days_ahead: int = 30, filters: Optional[ChartFilters] = None
    ) -> List[UpcomingInstallmentRow]:
        today = date.today()
        date_to = today + timedelta(days=days_ahead + 1)
        installments = self._installment_repository.find_all(
            status=InstallmentStatus.PENDING, date_from=today, date_to=date_to
        )
        if not installments:
            return []

        plans = {p.id: p for p in self._installment_plan_repository.find_all()}
        purchases_by_id = {p.id: p for p in self._purchase_repository.find_all()}

        rows: List[UpcomingInstallmentRow] = []
        for inst in installments:
            plan = plans.get(inst.installment_plan_id)
            if plan is None:
                continue
            purchase = purchases_by_id.get(plan.purchase_id)
            if purchase is None:
                continue
            event = self._financial_event_repository.find_by_id(purchase.financial_event_id)
            if event is None or not self._matches_filters(event, filters):
                continue
            rows.append(UpcomingInstallmentRow(
                due_date=inst.due_date,
                description=event.description,
                amount=inst.amount,
                installment_number=inst.installment_number,
                installment_count=plan.installment_count,
                event_id=event.id,
            ))

        rows.sort(key=lambda r: r.due_date)
        return rows

    def get_upcoming_recurring_occurrences(
        self, days_ahead: int = 30, filters: Optional[ChartFilters] = None
    ) -> List[UpcomingRecurringOccurrenceRow]:
        today = date.today()
        date_to = today + timedelta(days=days_ahead + 1)
        rules = self._recurring_event_repository.find_all(is_active=True)

        rows: List[UpcomingRecurringOccurrenceRow] = []
        for rule in rules:
            if not self._matches_filters(rule, filters):
                continue
            confirmed = {
                e.event_date for e in self._financial_event_repository.find_all(recurring_event_id=rule.id)
            }
            skipped = set(self._recurring_event_repository.find_skips(rule.id))
            pending_dates = self._recurring_event_service.compute_pending_occurrences(
                rule, today, date_to, confirmed, skipped
            )
            for occurrence_date in pending_dates:
                rows.append(UpcomingRecurringOccurrenceRow(
                    occurrence_date=occurrence_date,
                    description=rule.description,
                    amount=rule.amount,
                    recurring_event_id=rule.id,
                    frequency_label=_frequency_label(rule),
                ))

        rows.sort(key=lambda r: r.occurrence_date)
        return rows

    def get_credit_card_utilization(
        self, filters: Optional[ChartFilters] = None
    ) -> List[CreditCardUtilizationRow]:
        cards = self._credit_card_repository.find_all()
        if filters and filters.credit_card_ids:
            cards = [c for c in cards if c.id in filters.credit_card_ids]

        rows = []
        for card in cards:
            if not card.is_active:
                continue
            status = self._credit_card_service.get_status(card)
            rows.append(CreditCardUtilizationRow(
                credit_card_id=card.id,
                credit_card_name=card.name,
                current_debt=status.current_debt,
                credit_limit=card.credit_limit,
                available_credit=status.available_credit,
            ))
        return rows

    # -- breakdown helpers --------------------------------------------------

    def _breakdown_by_category(
        self, metrics: List[MetricType], date_range: DateRangeSpec, filters: Optional[ChartFilters]
    ) -> BreakdownResult:
        date_from, date_to = self.resolve_date_range(date_range)
        merged: Dict[Optional[str], Dict[str, float]] = {}
        for year, month in _month_range(date_from, date_to):
            breakdown = self._category_breakdown_service.get_breakdown(year, month)
            for item in breakdown.items:
                bucket = merged.setdefault(item.category_id, {"income": 0.0, "expenses": 0.0})
                bucket["income"] += item.total_income
                bucket["expenses"] += item.total_expenses

        if filters and filters.category_ids:
            merged = {k: v for k, v in merged.items() if k in filters.category_ids}

        category_names = {c.id: c.name for c in self._category_repository.find_all()}
        rows = []
        for category_id, bucket in merged.items():
            income, expenses = bucket["income"], bucket["expenses"]
            values = self._metric_values(metrics, income, expenses)
            label = category_names.get(category_id, "Uncategorized") if category_id else "Uncategorized"
            rows.append(BreakdownRow(dimension_id=category_id, dimension_label=label, values=values))
        rows.sort(key=lambda r: sum(r.values.values()), reverse=True)
        return BreakdownResult(rows=rows)

    def _breakdown_by_account(
        self, metrics: List[MetricType], date_range: DateRangeSpec, filters: Optional[ChartFilters]
    ) -> BreakdownResult:
        if MetricType.BALANCE in metrics:
            if len(metrics) > 1:
                raise ValueError("BALANCE cannot be combined with other metrics")
            summary = self._account_summary_service.get_summary(None, None)
        else:
            date_from, date_to = self.resolve_date_range(date_range)
            summary = self._account_summary_service.get_summary(date_from, date_to)

        items = summary.items
        if filters and filters.account_ids:
            items = [i for i in items if i.account_id in filters.account_ids]

        rows = []
        for item in items:
            values: Dict[str, float] = {}
            for metric in metrics:
                if metric == MetricType.INCOME:
                    values[metric.value] = item.total_income
                elif metric == MetricType.EXPENSES:
                    values[metric.value] = item.total_expenses
                elif metric == MetricType.NET:
                    values[metric.value] = item.total_income - item.total_expenses
                elif metric == MetricType.BALANCE:
                    values[metric.value] = item.current_balance
            rows.append(BreakdownRow(dimension_id=item.account_id, dimension_label=item.account_name, values=values))
        return BreakdownResult(rows=rows)

    def _breakdown_by_counterparty(
        self, metrics: List[MetricType], date_range: DateRangeSpec, filters: Optional[ChartFilters]
    ) -> BreakdownResult:
        date_from, date_to = self.resolve_date_range(date_range)
        events = self._events_in_range(date_from, date_to, filters)

        agg: Dict[Optional[str], Dict[str, float]] = {}
        for e in events:
            bucket = agg.setdefault(e.counterparty_id, {"income": 0.0, "expenses": 0.0})
            if e.event_type in INCOME_TYPES:
                bucket["income"] += e.amount
            elif e.event_type in EXPENSE_TYPES:
                bucket["expenses"] += e.amount

        labels = {c.id: c.name for c in self._counterparty_repository.find_all()}
        rows = []
        for counterparty_id, bucket in agg.items():
            values = self._metric_values(metrics, bucket["income"], bucket["expenses"])
            label = labels.get(counterparty_id, "No counterparty") if counterparty_id else "No counterparty"
            rows.append(BreakdownRow(dimension_id=counterparty_id, dimension_label=label, values=values))
        rows.sort(key=lambda r: sum(r.values.values()), reverse=True)
        return BreakdownResult(rows=rows)

    def _breakdown_credit_card_debt(self, filters: Optional[ChartFilters]) -> BreakdownResult:
        utilization = self.get_credit_card_utilization(filters)
        rows = [
            BreakdownRow(
                dimension_id=u.credit_card_id,
                dimension_label=u.credit_card_name,
                values={MetricType.CREDIT_CARD_DEBT.value: u.current_debt},
            )
            for u in utilization
        ]
        return BreakdownResult(rows=rows)

    def _breakdown_none(
        self, metrics: List[MetricType], date_range: DateRangeSpec, filters: Optional[ChartFilters]
    ) -> BreakdownResult:
        values: Dict[str, float] = {}
        income = expenses = 0.0
        if any(m in (MetricType.INCOME, MetricType.EXPENSES, MetricType.NET) for m in metrics):
            date_from, date_to = self.resolve_date_range(date_range)
            events = self._events_in_range(date_from, date_to, filters)
            income, expenses = self._classify(events)

        for metric in metrics:
            if metric == MetricType.INCOME:
                values[metric.value] = income
            elif metric == MetricType.EXPENSES:
                values[metric.value] = expenses
            elif metric == MetricType.NET:
                values[metric.value] = income - expenses
            elif metric == MetricType.BALANCE:
                summary = self._account_summary_service.get_summary(None, None)
                items = summary.items
                if filters and filters.account_ids:
                    items = [i for i in items if i.account_id in filters.account_ids]
                values[metric.value] = sum(i.current_balance for i in items)
            elif metric == MetricType.CREDIT_CARD_DEBT:
                utilization = self.get_credit_card_utilization(filters)
                values[metric.value] = sum(u.current_debt for u in utilization)
            elif metric == MetricType.INSTALLMENT_DUE:
                date_from, date_to = self.resolve_date_range(date_range)
                installments = self._installment_repository.find_all(date_from=date_from, date_to=date_to)
                values[metric.value] = sum(i.amount for i in installments)

        return BreakdownResult(rows=[BreakdownRow(dimension_id=None, dimension_label="Total", values=values)])

    # -- shared low-level helpers --------------------------------------------

    def _events_in_range(self, date_from, date_to, filters: Optional[ChartFilters]):
        events = self._financial_event_repository.find_all(date_from=date_from, date_to=date_to)
        if filters is None:
            return events
        return [e for e in events if self._matches_filters(e, filters)]

    @staticmethod
    def _classify(events) -> Tuple[float, float]:
        income = sum(e.amount for e in events if e.event_type in INCOME_TYPES)
        expenses = sum(e.amount for e in events if e.event_type in EXPENSE_TYPES)
        return income, expenses

    @staticmethod
    def _metric_values(metrics: List[MetricType], income: float, expenses: float) -> Dict[str, float]:
        values: Dict[str, float] = {}
        for metric in metrics:
            if metric == MetricType.INCOME:
                values[metric.value] = income
            elif metric == MetricType.EXPENSES:
                values[metric.value] = expenses
            elif metric == MetricType.NET:
                values[metric.value] = income - expenses
        return values

    @staticmethod
    def _matches_filters(event, filters: Optional[ChartFilters]) -> bool:
        if filters is None:
            return True
        if filters.account_ids and event.account_id not in filters.account_ids \
                and event.destination_account_id not in filters.account_ids:
            return False
        if filters.category_ids and event.category_id not in filters.category_ids:
            return False
        if filters.counterparty_ids and event.counterparty_id not in filters.counterparty_ids:
            return False
        if filters.credit_card_ids and event.credit_card_id not in filters.credit_card_ids:
            return False
        return True
