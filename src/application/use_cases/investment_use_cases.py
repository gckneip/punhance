from datetime import date, datetime
from typing import List, Optional

from src.domain.entities.investment import Investment, AssetType
from src.domain.entities.investment_transaction import InvestmentTransaction, InvestmentTxnType
from src.domain.entities.investment_schedule import InvestmentSchedule
from src.domain.entities.portfolio_snapshot import PortfolioSnapshot
from src.domain.repositories.investment_repository import InvestmentRepository
from src.domain.repositories.investment_transaction_repository import (
    InvestmentTransactionRepository,
)
from src.domain.repositories.investment_schedule_repository import (
    InvestmentScheduleRepository,
)
from src.domain.repositories.portfolio_snapshot_repository import (
    PortfolioSnapshotRepository,
)
from src.domain.services.investment_service import InvestmentService, PortfolioSummary
from src.domain.services import investment_schedule_service as sched_service
from src.application.dto.investment_schedule_dto import (
    CreateInvestmentScheduleDTO, InvestmentScheduleDTO,
)
from src.application.dto.investment_dto import CreateInvestmentDTO, InvestmentDTO
from src.application.dto.investment_transaction_dto import (
    CreateInvestmentTransactionDTO,
    InvestmentTransactionDTO,
)


# Asset types whose current_price is a total value (renda fixa, caixinhas) rather
# than a per-unit price. For these, the value entered at creation doubles as the
# initial invested amount, so we seed a matching CONTRIBUTION. Quantity-based types
# (stocks, crypto, foreign equities) build their basis from real BUY transactions.
_AMOUNT_BASED_ASSET_TYPES = (
    AssetType.RENDA_FIXA,
    AssetType.SAVINGS_BOX,
    AssetType.OTHER,
)


class InvestmentUseCases:
    def __init__(
        self,
        investment_repository: InvestmentRepository,
        transaction_repository: InvestmentTransactionRepository,
        investment_service: InvestmentService,
        portfolio_snapshot_repository: PortfolioSnapshotRepository = None,
        schedule_repository: InvestmentScheduleRepository = None,
    ):
        self._repository = investment_repository
        self._txn_repository = transaction_repository
        self._service = investment_service
        self._snapshot_repository = portfolio_snapshot_repository
        self._schedule_repository = schedule_repository

    def record_snapshot(self) -> None:
        """Record today's portfolio totals (upsert by date) so a
        portfolio-value-over-time chart can accrue history. No-op if no snapshot
        repository is wired."""
        if self._snapshot_repository is None:
            return
        summary = self.get_portfolio_summary()
        self._snapshot_repository.upsert(PortfolioSnapshot(
            date=date.today().isoformat(),
            total_invested=summary.total_invested,
            total_market_value=summary.total_market_value,
            total_gain=summary.total_gain,
            total_income=summary.total_income,
        ))

    # ---- Holdings -------------------------------------------------------
    def create_investment(self, dto: CreateInvestmentDTO) -> InvestmentDTO:
        investment = Investment(
            name=dto.name,
            asset_type=dto.asset_type,
            currency=dto.currency,
            ticker=dto.ticker,
            account_id=dto.account_id,
            current_price=dto.current_price,
            price_updated_at=datetime.now().isoformat(timespec="seconds")
            if dto.current_price
            else None,
            goal_amount=dto.goal_amount,
            goal_date=dto.goal_date,
            yield_rate=dto.yield_rate,
            yield_index=dto.yield_index,
            monthly_contribution=dto.monthly_contribution,
            maturity_date=dto.maturity_date,
            is_active=dto.is_active,
            notes=dto.notes,
        )
        self._repository.save(investment)
        # Seed the invested principal for amount-based holdings: their current_price
        # is a total value, so it also stands in as the initial contribution.
        # Without this the holding would report a market value but zero invested,
        # inflating its apparent gain.
        if dto.current_price and investment.asset_type in _AMOUNT_BASED_ASSET_TYPES:
            self._txn_repository.save(InvestmentTransaction(
                investment_id=investment.id,
                txn_type=InvestmentTxnType.CONTRIBUTION,
                date=date.today().isoformat(),
                total=dto.current_price,
            ))
        return self._to_dto(investment)

    def update_investment(
        self, investment_id: str, dto: CreateInvestmentDTO
    ) -> Optional[InvestmentDTO]:
        investment = self._repository.find_by_id(investment_id)
        if investment is None:
            return None
        if dto.current_price != investment.current_price:
            investment.price_updated_at = datetime.now().isoformat(timespec="seconds")
        investment.name = dto.name
        investment.asset_type = dto.asset_type
        investment.currency = dto.currency
        investment.ticker = dto.ticker
        investment.account_id = dto.account_id
        investment.current_price = dto.current_price
        investment.goal_amount = dto.goal_amount
        investment.goal_date = dto.goal_date
        investment.yield_rate = dto.yield_rate
        investment.yield_index = dto.yield_index
        investment.monthly_contribution = dto.monthly_contribution
        investment.maturity_date = dto.maturity_date
        investment.is_active = dto.is_active
        investment.notes = dto.notes
        self._repository.save(investment)
        return self._to_dto(investment)

    def update_price(self, investment_id: str, price: float) -> Optional[InvestmentDTO]:
        investment = self._repository.find_by_id(investment_id)
        if investment is None:
            return None
        investment.current_price = price
        investment.price_updated_at = datetime.now().isoformat(timespec="seconds")
        self._repository.save(investment)
        return self._to_dto(investment)

    def add_savings_movement(
        self,
        box_id: str,
        direction: str,
        amount: float,
        txn_date: str,
        notes: Optional[str] = None,
    ) -> Optional[InvestmentDTO]:
        """Record a deposit (aporte) or withdrawal (resgate) on a savings box and
        move its balance by the same amount.

        A savings box tracks a single balance (``current_price``), not a quantity
        of priced units, so the transaction carries only a total — no quantity /
        unit price / fees. ``direction`` is ``"deposit"`` or ``"withdraw"``.
        Depositing raises the balance and the invested principal together (so the
        yield figure is unchanged); withdrawing lowers both. Accrued yield is
        recorded separately via :meth:`update_price` ("update balance").
        """
        box = self._repository.find_by_id(box_id)
        if box is None:
            return None
        is_deposit = direction == "deposit"
        txn_type = (
            InvestmentTxnType.CONTRIBUTION if is_deposit else InvestmentTxnType.WITHDRAWAL
        )
        self._txn_repository.save(InvestmentTransaction(
            investment_id=box_id,
            txn_type=txn_type,
            date=txn_date,
            quantity=0.0,
            unit_price=0.0,
            fees=0.0,
            total=amount,
            notes=notes,
        ))
        delta = amount if is_deposit else -amount
        box.current_price = max((box.current_price or 0.0) + delta, 0.0)
        box.price_updated_at = datetime.now().isoformat(timespec="seconds")
        self._repository.save(box)
        return self._to_dto(box)

    def list_investments(self) -> List[InvestmentDTO]:
        return [self._to_dto(i) for i in self._repository.find_all()]

    def get_investment(self, investment_id: str) -> Optional[InvestmentDTO]:
        investment = self._repository.find_by_id(investment_id)
        return self._to_dto(investment) if investment else None

    def delete_investment(self, investment_id: str) -> None:
        self._txn_repository.delete_by_investment(investment_id)
        if self._schedule_repository is not None:
            self._schedule_repository.delete_by_investment(investment_id)
        self._repository.delete(investment_id)

    # ---- Scheduled contributions ---------------------------------------
    def add_schedule(self, dto: CreateInvestmentScheduleDTO) -> InvestmentScheduleDTO:
        schedule = InvestmentSchedule(
            investment_id=dto.investment_id,
            amount=dto.amount,
            frequency=dto.frequency,
            start_date=dto.start_date,
            interval=dto.interval,
            end_date=dto.end_date,
            is_active=dto.is_active,
        )
        self._schedule_repository.save(schedule)
        return self._schedule_to_dto(schedule)

    def update_schedule(
        self, schedule_id: str, dto: CreateInvestmentScheduleDTO
    ) -> Optional[InvestmentScheduleDTO]:
        schedule = self._schedule_repository.find_by_id(schedule_id)
        if schedule is None:
            return None
        schedule.amount = dto.amount
        schedule.frequency = dto.frequency
        schedule.start_date = dto.start_date
        schedule.interval = dto.interval
        schedule.end_date = dto.end_date
        schedule.is_active = dto.is_active
        self._schedule_repository.save(schedule)
        return self._schedule_to_dto(schedule)

    def list_schedules(self, investment_id: str) -> List[InvestmentScheduleDTO]:
        return [
            self._schedule_to_dto(s)
            for s in self._schedule_repository.find_by_investment(investment_id)
        ]

    def delete_schedule(self, schedule_id: str) -> None:
        self._schedule_repository.delete(schedule_id)

    def generate_due_schedules(self, today: date = None) -> int:
        """Materialize past-due scheduled contributions as real CONTRIBUTION
        transactions. Idempotent via each schedule's last_generated_date."""
        if self._schedule_repository is None:
            return 0
        today = today or date.today()
        generated = 0
        for sched in self._schedule_repository.find_all_active():
            inv = self._repository.find_by_id(sched.investment_id)
            if inv is None:
                continue
            start = date.fromisoformat(sched.start_date)
            end = date.fromisoformat(sched.end_date) if sched.end_date else None
            occ = sched_service.occurrences_between(
                sched.frequency, sched.interval, start, start, today, end
            )
            watermark = (
                date.fromisoformat(sched.last_generated_date)
                if sched.last_generated_date else None
            )
            pending = [o for o in occ if watermark is None or o > watermark]
            if not pending:
                continue
            # Amount-based holdings (no per-unit quantity) grow in value with each
            # deposit; quantity-based ones only get the contribution recorded.
            position = self._service.compute_position(
                inv, self._txn_repository.find_by_investment(inv.id)
            )
            is_amount_based = position.quantity == 0
            for occurrence in pending:
                self._txn_repository.save(InvestmentTransaction(
                    investment_id=inv.id,
                    txn_type=InvestmentTxnType.CONTRIBUTION,
                    date=occurrence.isoformat(),
                    total=sched.amount,
                    notes=None,
                ))
                generated += 1
            if is_amount_based:
                inv.current_price += sched.amount * len(pending)
                inv.price_updated_at = datetime.now().isoformat(timespec="seconds")
                self._repository.save(inv)
            sched.last_generated_date = pending[-1].isoformat()
            self._schedule_repository.save(sched)
        return generated

    def _schedule_to_dto(self, schedule: InvestmentSchedule) -> InvestmentScheduleDTO:
        start = date.fromisoformat(schedule.start_date)
        end = date.fromisoformat(schedule.end_date) if schedule.end_date else None
        nxt = sched_service.next_occurrence(
            schedule.frequency, schedule.interval, start, date.today(), end
        )
        return InvestmentScheduleDTO(
            id=schedule.id,
            investment_id=schedule.investment_id,
            amount=schedule.amount,
            frequency=schedule.frequency,
            start_date=schedule.start_date,
            interval=schedule.interval,
            end_date=schedule.end_date,
            last_generated_date=schedule.last_generated_date,
            is_active=schedule.is_active,
            next_date=nxt.isoformat() if nxt else None,
        )

    def get_portfolio_summary(self) -> PortfolioSummary:
        investments = self._repository.find_all()
        txns_by_investment = {
            inv.id: self._txn_repository.find_by_investment(inv.id)
            for inv in investments
        }
        return self._service.compute_portfolio(investments, txns_by_investment)

    # ---- Transactions ---------------------------------------------------
    def add_transaction(
        self, dto: CreateInvestmentTransactionDTO
    ) -> InvestmentTransactionDTO:
        transaction = InvestmentTransaction(
            investment_id=dto.investment_id,
            txn_type=dto.txn_type,
            date=dto.date,
            quantity=dto.quantity,
            unit_price=dto.unit_price,
            fees=dto.fees,
            total=dto.total,
            notes=dto.notes,
        )
        self._txn_repository.save(transaction)
        return self._txn_to_dto(transaction)

    def update_transaction(
        self, transaction_id: str, dto: CreateInvestmentTransactionDTO
    ) -> Optional[InvestmentTransactionDTO]:
        transaction = self._txn_repository.find_by_id(transaction_id)
        if transaction is None:
            return None
        transaction.txn_type = dto.txn_type
        transaction.date = dto.date
        transaction.quantity = dto.quantity
        transaction.unit_price = dto.unit_price
        transaction.fees = dto.fees
        transaction.total = dto.total
        transaction.notes = dto.notes
        self._txn_repository.save(transaction)
        return self._txn_to_dto(transaction)

    def list_transactions(self, investment_id: str) -> List[InvestmentTransactionDTO]:
        return [
            self._txn_to_dto(t)
            for t in self._txn_repository.find_by_investment(investment_id)
        ]

    def delete_transaction(self, transaction_id: str) -> None:
        self._txn_repository.delete(transaction_id)

    # ---- Finance-event contribution sync --------------------------------
    def get_event_investment_id(self, financial_event_id: str) -> Optional[str]:
        """Which holding a finance investment event contributes to, if any."""
        txn = self._txn_repository.find_by_financial_event(financial_event_id)
        return txn.investment_id if txn is not None else None

    def sync_event_contribution(
        self, financial_event_id: str, investment_id: Optional[str],
        amount: float, txn_date: str, notes: Optional[str] = None,
    ) -> None:
        """Keep a Contribution transaction in step with a finance investment
        event: create/update it for the chosen holding, or drop it when no
        holding is set (or the amount is non-positive)."""
        existing = self._txn_repository.find_by_financial_event(financial_event_id)
        if not investment_id or amount <= 0:
            if existing is not None:
                self._txn_repository.delete(existing.id)
                self.record_snapshot()
            return
        txn = existing or InvestmentTransaction(
            investment_id=investment_id,
            txn_type=InvestmentTxnType.CONTRIBUTION,
            date=txn_date,
            financial_event_id=financial_event_id,
        )
        txn.investment_id = investment_id
        txn.txn_type = InvestmentTxnType.CONTRIBUTION
        txn.date = txn_date
        txn.quantity = 0.0
        txn.unit_price = 0.0
        txn.fees = 0.0
        txn.total = amount
        txn.notes = notes
        self._txn_repository.save(txn)
        self.record_snapshot()

    def delete_event_contribution(self, financial_event_id: str) -> None:
        if self._txn_repository.find_by_financial_event(financial_event_id) is not None:
            self._txn_repository.delete_by_financial_event(financial_event_id)
            self.record_snapshot()

    # ---- Mapping --------------------------------------------------------
    def _to_dto(self, investment: Investment) -> InvestmentDTO:
        transactions = self._txn_repository.find_by_investment(investment.id)
        position = self._service.compute_position(investment, transactions)
        return InvestmentDTO(
            id=investment.id,
            name=investment.name,
            asset_type=investment.asset_type,
            currency=investment.currency,
            ticker=investment.ticker,
            account_id=investment.account_id,
            current_price=investment.current_price,
            price_updated_at=investment.price_updated_at,
            goal_amount=investment.goal_amount,
            goal_date=investment.goal_date,
            yield_rate=investment.yield_rate,
            yield_index=investment.yield_index,
            monthly_contribution=investment.monthly_contribution,
            maturity_date=investment.maturity_date,
            is_active=investment.is_active,
            notes=investment.notes,
            quantity=position.quantity,
            net_invested=position.net_invested,
            avg_unit_price=position.avg_unit_price,
            market_value=position.market_value,
            income_total=position.income_total,
            unrealized_gain=position.unrealized_gain,
            total_return=position.total_return,
            return_pct=position.return_pct,
            goal_progress_pct=position.goal_progress_pct,
        )

    def _txn_to_dto(
        self, transaction: InvestmentTransaction
    ) -> InvestmentTransactionDTO:
        return InvestmentTransactionDTO(
            id=transaction.id,
            investment_id=transaction.investment_id,
            txn_type=transaction.txn_type,
            date=transaction.date,
            quantity=transaction.quantity,
            unit_price=transaction.unit_price,
            fees=transaction.fees,
            total=transaction.total,
            notes=transaction.notes,
        )
