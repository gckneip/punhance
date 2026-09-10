from datetime import date
from typing import Dict, List, Optional

from src.application.dto.homebank_dto import HomeBankImportPlanDTO, HomeBankImportResultDTO
from src.application.dto.purchase_dto import CreatePurchaseDTO, CreatePurchaseItemDTO
from src.application.dto.recurring_event_dto import CreateRecurringEventDTO
from src.application.use_cases.purchase_use_cases import PurchaseUseCases
from src.application.use_cases.recurring_event_use_cases import RecurringEventUseCases
from src.domain.entities.account import Account, AccountType
from src.domain.entities.category import Category
from src.domain.entities.counterparty import Counterparty
from src.domain.entities.credit_card import CreditCard
from src.domain.entities.financial_event import EventType, FinancialEvent
from src.domain.entities.purchase import PaymentMethod
from src.domain.entities.recurring_event import RecurrenceFrequency, RecurringEvent
from src.domain.repositories.account_repository import AccountRepository
from src.domain.repositories.category_repository import CategoryRepository
from src.domain.repositories.counterparty_repository import CounterpartyRepository
from src.domain.repositories.credit_card_repository import CreditCardRepository
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.services.recurring_event_service import RecurringEventService
from src.infrastructure.homebank.date_utils import julian_to_date
from src.infrastructure.homebank.mapping import (
    HB_ACCOUNT_TYPE_CREDITCARD, HB_ACCOUNT_TYPE_TO_OURS, HB_PAYMODE_TO_PAYMENT_METHOD,
)
from src.infrastructure.homebank.xhb_models import HbFav, HbFile, HbOperation
from src.infrastructure.homebank.xhb_reader import XhbReader

_CATEGORY_PALETTE = [
    "#4C6EF5", "#F76707", "#37B24D", "#E64980", "#7048E8",
    "#12B886", "#F59F00", "#1098AD", "#E8590C", "#5C7CFA",
]
_MAX_WARNINGS = 200
_FREQUENCY_BY_HB_UNIT = {
    0: RecurrenceFrequency.DAILY,
    1: RecurrenceFrequency.WEEKLY,
    2: RecurrenceFrequency.MONTHLY,
    3: RecurrenceFrequency.YEARLY,
}


class HomeBankImportPlan:
    """Pure, unsaved staging area for one .xhb import: fully-built domain
    entities/DTOs plus warnings, built by build_import_plan and handed
    unchanged to commit_import_plan so entity ids stay stable between the
    preview and the write."""

    def __init__(self, hb_file: HbFile):
        self.hb_file = hb_file
        self.accounts: List[Account] = []
        self.credit_cards: List[CreditCard] = []
        self.categories: List[Category] = []
        self.counterparties: List[Counterparty] = []
        self.events: List[FinancialEvent] = []
        self.purchase_dtos: List[CreatePurchaseDTO] = []
        self.recurring_dtos: List[CreateRecurringEventDTO] = []
        self.warnings: List[str] = []
        self.skipped_operations = 0
        self.transfer_count = 0

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def counts(self) -> Dict[str, int]:
        return {
            "accounts": len(self.accounts),
            "credit_cards": len(self.credit_cards),
            "categories": len(self.categories),
            "counterparties": len(self.counterparties),
            "events": len(self.events) - self.transfer_count,
            "transfers": self.transfer_count,
            "purchases": len(self.purchase_dtos),
            "recurring_events": len(self.recurring_dtos),
            "skipped_operations": self.skipped_operations,
        }

    def to_preview_dto(self) -> HomeBankImportPlanDTO:
        truncated = len(self.warnings) > _MAX_WARNINGS
        capped = self.warnings[:_MAX_WARNINGS]
        if truncated:
            capped = capped + [f"... and {len(self.warnings) - _MAX_WARNINGS} more warnings"]
        return HomeBankImportPlanDTO(counts=self.counts, warnings=capped, warnings_truncated=truncated)


class HomeBankImportUseCases:
    def __init__(
        self,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        counterparty_repository: CounterpartyRepository,
        credit_card_repository: CreditCardRepository,
        financial_event_repository: FinancialEventRepository,
        purchase_use_cases: PurchaseUseCases,
        recurring_event_use_cases: RecurringEventUseCases,
        reader: XhbReader,
        conn,
    ):
        self._account_repo = account_repository
        self._category_repo = category_repository
        self._counterparty_repo = counterparty_repository
        self._credit_card_repo = credit_card_repository
        self._event_repo = financial_event_repository
        self._purchase_use_cases = purchase_use_cases
        self._recurring_event_use_cases = recurring_event_use_cases
        self._reader = reader
        self._conn = conn
        self._recurring_service = RecurringEventService()

    def build_import_plan(self, path: str) -> HomeBankImportPlan:
        hb_file = self._reader.parse(path)
        plan = HomeBankImportPlan(hb_file)

        currency_by_key = {c.key: c.iso for c in hb_file.currencies}
        account_key_to_account: Dict[int, Account] = {}
        account_key_to_credit_card: Dict[int, CreditCard] = {}
        account_key_to_currency: Dict[int, str] = {}

        for hb_acc in hb_file.accounts:
            account_key_to_currency[hb_acc.key] = currency_by_key.get(hb_acc.curr, "BRL")
            if hb_acc.type == HB_ACCOUNT_TYPE_CREDITCARD:
                card = CreditCard(
                    name=hb_acc.name or f"Card {hb_acc.key}",
                    issuer="Imported",
                    credit_limit=0.0,
                    closing_day=1,
                    due_day=10,
                )
                account_key_to_credit_card[hb_acc.key] = card
                plan.credit_cards.append(card)
                plan.add_warning(
                    f"Credit card '{card.name}' was imported with placeholder issuer/limit/"
                    f"closing day/due day - HomeBank does not store these, please review."
                )
            else:
                our_type = HB_ACCOUNT_TYPE_TO_OURS.get(hb_acc.type)
                if our_type is None:
                    our_type = AccountType.CASH
                    plan.add_warning(
                        f"Account '{hb_acc.name}' has an unrecognized HomeBank type "
                        f"({hb_acc.type}) - imported as Cash."
                    )
                elif hb_acc.type in (3, 5):
                    label = "asset" if hb_acc.type == 3 else "liability"
                    plan.add_warning(
                        f"Account '{hb_acc.name}' is a HomeBank {label} account with no exact "
                        f"equivalent here - imported as {our_type.value}, please review."
                    )
                account = Account(
                    name=hb_acc.name or f"Account {hb_acc.key}",
                    type=our_type,
                    initial_balance=hb_acc.initial,
                )
                account_key_to_account[hb_acc.key] = account
                plan.accounts.append(account)

        category_key_to_category: Dict[int, Category] = {}
        for i, hb_cat in enumerate(hb_file.categories):
            category = Category(
                name=hb_cat.name or f"Category {hb_cat.key}",
                color=_CATEGORY_PALETTE[i % len(_CATEGORY_PALETTE)],
            )
            category_key_to_category[hb_cat.key] = category
            plan.categories.append(category)
        for hb_cat in hb_file.categories:
            if not hb_cat.parent or hb_cat.parent == hb_cat.key:
                continue
            parent = category_key_to_category.get(hb_cat.parent)
            if parent is None:
                plan.add_warning(
                    f"Category '{hb_cat.name}' references an unknown parent category - "
                    f"imported as top-level."
                )
                continue
            category_key_to_category[hb_cat.key].parent_id = parent.id

        payee_key_to_counterparty: Dict[int, Counterparty] = {}
        for hb_pay in hb_file.payees:
            counterparty = Counterparty(name=hb_pay.name or f"Payee {hb_pay.key}")
            payee_key_to_counterparty[hb_pay.key] = counterparty
            plan.counterparties.append(counterparty)

        def resolve_account_id(key: int) -> Optional[str]:
            account = account_key_to_account.get(key)
            return account.id if account else None

        def resolve_credit_card(key: int) -> Optional[CreditCard]:
            return account_key_to_credit_card.get(key)

        def resolve_category_id(key: int) -> Optional[str]:
            category = category_key_to_category.get(key)
            return category.id if category else None

        def resolve_category_name(key: int) -> Optional[str]:
            category = category_key_to_category.get(key)
            return category.name if category else None

        def resolve_counterparty_id(key: int) -> Optional[str]:
            counterparty = payee_key_to_counterparty.get(key)
            return counterparty.id if counterparty else None

        self._process_operations(
            plan, hb_file.operations, account_key_to_currency, resolve_account_id,
            resolve_credit_card, resolve_category_id, resolve_category_name, resolve_counterparty_id,
        )

        for hb_fav in hb_file.favs:
            self._process_fav(
                plan, hb_fav, resolve_account_id, resolve_credit_card,
                resolve_category_id, resolve_counterparty_id,
            )

        return plan

    def _process_operations(
        self, plan, operations: List[HbOperation], account_key_to_currency, resolve_account_id,
        resolve_credit_card, resolve_category_id, resolve_category_name, resolve_counterparty_id,
    ) -> None:
        transfer_candidates = [op for op in operations if op.is_transfer]
        regular_ops = [op for op in operations if not op.is_transfer]

        groups: Dict[object, List[HbOperation]] = {}
        for op in transfer_candidates:
            key = op.kxfer if op.kxfer else ("_no_kxfer", id(op))
            groups.setdefault(key, []).append(op)

        for key, group in groups.items():
            if len(group) == 2:
                self._emit_transfer_pair(plan, group[0], group[1], resolve_account_id)
            elif len(group) == 1:
                plan.add_warning(
                    f"Transfer on {julian_to_date(group[0].date)} has no matching counterpart "
                    f"row (kxfer={key}) - imported as a plain income/expense, destination lost."
                )
                regular_ops.append(group[0])
            else:
                neg = next((o for o in group if o.amount < 0), None)
                pos = next((o for o in group if o.amount > 0 and o is not neg), None)
                if neg is not None and pos is not None:
                    self._emit_transfer_pair(plan, neg, pos, resolve_account_id)
                    leftovers = [o for o in group if o is not neg and o is not pos]
                else:
                    leftovers = group
                if leftovers:
                    plan.add_warning(
                        f"kxfer={key} was shared by {len(group)} rows (expected 2) - "
                        f"{len(leftovers)} extra row(s) imported as plain income/expense."
                    )
                    regular_ops.extend(leftovers)

        for op in regular_ops:
            if op.split_flag_set and not op.scat:
                plan.add_warning(
                    f"Operation on {julian_to_date(op.date)} ('{op.wording}') has the split "
                    f"flag set but no split data - imported as a single row."
                )
            elif op.scat and not op.split_flag_set:
                plan.add_warning(
                    f"Operation on {julian_to_date(op.date)} ('{op.wording}') has split data "
                    f"without the split flag - imported as a split anyway."
                )
            if op.is_split:
                self._emit_split_purchase(
                    plan, op, resolve_account_id, resolve_credit_card,
                    resolve_category_id, resolve_category_name, resolve_counterparty_id,
                )
            else:
                self._emit_plain_operation(
                    plan, op, account_key_to_currency, resolve_account_id,
                    resolve_credit_card, resolve_category_id, resolve_counterparty_id,
                )

    def _emit_transfer_pair(
        self, plan, op_a: HbOperation, op_b: HbOperation, resolve_account_id,
    ) -> None:
        if op_a.amount < 0:
            source, dest = op_a, op_b
        elif op_b.amount < 0:
            source, dest = op_b, op_a
        else:
            source, dest = op_a, op_b
            plan.add_warning(
                f"Transfer pair on {julian_to_date(op_a.date)} has no negative-amount leg - "
                f"direction may be wrong."
            )

        source_account_id = resolve_account_id(source.account)
        dest_account_id = resolve_account_id(source.dst_account) or resolve_account_id(dest.account)
        if source_account_id is None or dest_account_id is None:
            plan.add_warning(
                f"Transfer on {julian_to_date(source.date)} references an unresolved account - skipped."
            )
            plan.skipped_operations += 1
            return

        if abs(abs(source.amount) - abs(dest.amount)) > 0.01:
            plan.add_warning(
                f"Transfer on {julian_to_date(source.date)}: leg amounts differ "
                f"(R$ {abs(source.amount):.2f} vs R$ {abs(dest.amount):.2f}) - used the source leg."
            )
        if source.date != dest.date:
            plan.add_warning(
                f"Transfer legs on {julian_to_date(source.date)}/{julian_to_date(dest.date)} "
                f"have different dates - used the source leg's date."
            )

        plan.events.append(FinancialEvent(
            event_type=EventType.TRANSFER,
            event_date=julian_to_date(source.date),
            description=source.wording or dest.wording or "Transfer",
            amount=abs(source.amount),
            account_id=source_account_id,
            destination_account_id=dest_account_id,
        ))
        plan.transfer_count += 1

    def _build_notes(self, op: HbOperation) -> Optional[str]:
        parts = []
        if op.info:
            parts.append(f"Ref: {op.info}")
        if op.tags:
            parts.append(f"Tags: {op.tags}")
        if op.st == 4:
            parts.append("[HomeBank: void]")
        return "; ".join(parts) if parts else None

    def _emit_plain_operation(
        self, plan, op: HbOperation, account_key_to_currency, resolve_account_id,
        resolve_credit_card, resolve_category_id, resolve_counterparty_id,
    ) -> None:
        description = op.wording or "(no description)"
        notes = self._build_notes(op)
        credit_card = resolve_credit_card(op.account)

        if credit_card is not None:
            # Every row against a credit-card account becomes a Purchase (even
            # with a single implicit item) so it's counted by
            # CreditCardService, which sums debt via installments only.
            plan.purchase_dtos.append(CreatePurchaseDTO(
                event_date=julian_to_date(op.date),
                description=description,
                total_amount=abs(op.amount),
                payment_method=PaymentMethod.CREDIT_CARD,
                credit_card_id=credit_card.id,
                counterparty_id=resolve_counterparty_id(op.payee),
                notes=notes,
                installment_count=1,
                category_id=resolve_category_id(op.category),
            ))
            return

        account_id = resolve_account_id(op.account)
        if account_id is None:
            plan.skipped_operations += 1
            return

        amount_positive = op.amount >= 0
        if op.is_income != amount_positive:
            plan.add_warning(
                f"Operation on {julian_to_date(op.date)} ('{description}') has an income flag "
                f"that disagrees with its amount sign - used the amount sign."
            )
        event_type = EventType.INCOME if amount_positive else EventType.EXPENSE

        plan.events.append(FinancialEvent(
            event_type=event_type,
            event_date=julian_to_date(op.date),
            description=description,
            amount=abs(op.amount),
            category_id=resolve_category_id(op.category),
            account_id=account_id,
            counterparty_id=resolve_counterparty_id(op.payee),
            currency=account_key_to_currency.get(op.account, "BRL"),
            notes=notes,
        ))

    def _emit_split_purchase(
        self, plan, op: HbOperation, resolve_account_id, resolve_credit_card,
        resolve_category_id, resolve_category_name, resolve_counterparty_id,
    ) -> None:
        credit_card = resolve_credit_card(op.account)
        account_id = resolve_account_id(op.account)
        if credit_card is None and account_id is None:
            plan.skipped_operations += 1
            return

        cats = op.scat.split("||")
        amts = op.samt.split("||") if op.samt else []
        mems = op.smem.split("||") if op.smem else []
        n = len(cats)
        if amts:
            n = min(n, len(amts))
        if op.smem:
            n = min(n, len(mems))
        if len(cats) != len(amts) or (op.smem and len(mems) != len(cats)):
            plan.add_warning(
                f"Split operation on {julian_to_date(op.date)} ('{op.wording}') has mismatched "
                f"scat/samt/smem lengths - truncated to {n} item(s)."
            )

        items = []
        for i in range(n):
            cat_raw = cats[i].strip()
            cat_key = int(float(cat_raw)) if cat_raw else 0
            try:
                amt = float(amts[i])
            except (ValueError, IndexError):
                amt = 0.0
            mem = mems[i].strip() if i < len(mems) else ""
            category_id = resolve_category_id(cat_key)
            name = mem or resolve_category_name(cat_key) or f"Split item {i + 1}"
            items.append(CreatePurchaseItemDTO(
                name=name, quantity=1.0, unit="UNIT",
                unit_price=abs(amt), total_price=abs(amt), category_id=category_id,
            ))

        items_total = round(sum(i.total_price for i in items), 2)
        if abs(items_total - abs(op.amount)) > 0.01:
            plan.add_warning(
                f"Split operation on {julian_to_date(op.date)} ('{op.wording}'): item total "
                f"(R$ {items_total:.2f}) differs from operation amount (R$ {abs(op.amount):.2f})."
            )

        if credit_card is not None:
            payment_method = PaymentMethod.CREDIT_CARD
            credit_card_id = credit_card.id
        else:
            payment_method = HB_PAYMODE_TO_PAYMENT_METHOD.get(op.paymode, PaymentMethod.CASH)
            credit_card_id = None
            if payment_method == PaymentMethod.CREDIT_CARD:
                payment_method = PaymentMethod.CASH
                plan.add_warning(
                    f"Split operation on {julian_to_date(op.date)} indicates a credit-card "
                    f"payment mode but isn't posted against a HomeBank credit-card account - "
                    f"imported as Cash."
                )

        plan.purchase_dtos.append(CreatePurchaseDTO(
            event_date=julian_to_date(op.date),
            description=op.wording or "(no description)",
            total_amount=abs(op.amount),
            payment_method=payment_method,
            credit_card_id=credit_card_id,
            counterparty_id=resolve_counterparty_id(op.payee),
            notes=self._build_notes(op),
            installment_count=1,
            items=items,
        ))

    def _process_fav(
        self, plan, hb_fav: HbFav, resolve_account_id, resolve_credit_card,
        resolve_category_id, resolve_counterparty_id,
    ) -> None:
        frequency = _FREQUENCY_BY_HB_UNIT.get(hb_fav.unit)
        if frequency is None:
            plan.add_warning(
                f"Scheduled transaction '{hb_fav.wording}' has an unknown recurrence unit "
                f"({hb_fav.unit}) - skipped."
            )
            return

        account_id = resolve_account_id(hb_fav.account)
        credit_card = resolve_credit_card(hb_fav.account)
        if account_id is None and credit_card is None:
            plan.add_warning(
                f"Scheduled transaction '{hb_fav.wording}' references an unresolved account - skipped."
            )
            return

        destination_account_id = resolve_account_id(hb_fav.dst_account) if hb_fav.dst_account else None
        start_date = julian_to_date(hb_fav.nextdate) if hb_fav.nextdate else date.today()
        interval = max(hb_fav.every, 1)

        day_of_month = None
        weekday = None
        month = None
        if frequency == RecurrenceFrequency.WEEKLY:
            weekday = start_date.weekday()
        elif frequency == RecurrenceFrequency.MONTHLY:
            day_of_month = start_date.day
        elif frequency == RecurrenceFrequency.YEARLY:
            day_of_month = start_date.day
            month = start_date.month

        end_date = None
        if hb_fav.limit and hb_fav.limit > 0:
            temp_rule = RecurringEvent(
                event_type=EventType.EXPENSE,
                description=hb_fav.wording or "",
                amount=abs(hb_fav.amount),
                frequency=frequency,
                start_date=start_date,
                interval=interval,
                day_of_month=day_of_month,
                weekday=weekday,
                month=month,
                end_date=None,
            )
            far_future = date(start_date.year + 50, 12, 31)
            occurrences = self._recurring_service.generate_occurrences(temp_rule, start_date, far_future)
            occurrences = occurrences[:hb_fav.limit]
            if occurrences:
                end_date = occurrences[-1]
            plan.add_warning(
                f"Scheduled transaction '{hb_fav.wording}': HomeBank's occurrence-count limit "
                f"({hb_fav.limit}) was converted to an end date ({end_date}) - an approximation, "
                f"not a stored value."
            )

        category_id = resolve_category_id(hb_fav.category)
        if hb_fav.scat:
            category_id = None
            plan.add_warning(
                f"Scheduled transaction '{hb_fav.wording}' has split categories, which "
                f"RecurringEvent doesn't support - imported using the total amount only, no category."
            )

        if destination_account_id:
            event_type = EventType.TRANSFER
        elif hb_fav.amount < 0:
            event_type = EventType.EXPENSE
        else:
            event_type = EventType.INCOME

        plan.recurring_dtos.append(CreateRecurringEventDTO(
            event_type=event_type,
            description=hb_fav.wording or "(no description)",
            amount=abs(hb_fav.amount),
            frequency=frequency,
            start_date=start_date,
            interval=interval,
            day_of_month=day_of_month,
            weekday=weekday,
            month=month,
            end_date=end_date,
            category_id=category_id,
            account_id=account_id,
            destination_account_id=destination_account_id,
            credit_card_id=credit_card.id if credit_card else None,
            counterparty_id=resolve_counterparty_id(hb_fav.payee),
        ))

    def commit_import_plan(self, plan: HomeBankImportPlan) -> HomeBankImportResultDTO:
        warnings: List[str] = []
        created_counts = {
            "accounts": 0, "credit_cards": 0, "categories": 0, "counterparties": 0,
            "events": 0, "purchases": 0, "recurring_events": 0,
        }

        for account in plan.accounts:
            self._account_repo.save(account)
            created_counts["accounts"] += 1

        for card in plan.credit_cards:
            self._credit_card_repo.save(card)
            created_counts["credit_cards"] += 1

        for category in plan.categories:
            self._category_repo.save(category)
            created_counts["categories"] += 1

        for counterparty in plan.counterparties:
            self._counterparty_repo.save(counterparty)
            created_counts["counterparties"] += 1

        for event in plan.events:
            self._event_repo.save(event, commit=False)
        self._conn.commit()
        created_counts["events"] = len(plan.events)

        for dto in plan.purchase_dtos:
            try:
                self._purchase_use_cases.create_purchase(dto)
                created_counts["purchases"] += 1
            except Exception as exc:
                warnings.append(f"Failed to import purchase '{dto.description}': {exc}")

        for dto in plan.recurring_dtos:
            try:
                self._recurring_event_use_cases.create_recurring_event(dto)
                created_counts["recurring_events"] += 1
            except Exception as exc:
                warnings.append(f"Failed to import recurring event '{dto.description}': {exc}")

        return HomeBankImportResultDTO(created_counts=created_counts, warnings=warnings)
