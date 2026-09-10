from datetime import date
from typing import Dict, Optional

from src.application.dto.homebank_dto import HomeBankExportOptionsDTO, HomeBankExportResultDTO
from src.application.use_cases.account_use_cases import AccountUseCases
from src.application.use_cases.category_use_cases import CategoryUseCases
from src.application.use_cases.counterparty_use_cases import CounterpartyUseCases
from src.application.use_cases.credit_card_use_cases import CreditCardUseCases
from src.application.use_cases.financial_event_use_cases import FinancialEventUseCases
from src.application.use_cases.purchase_use_cases import PurchaseUseCases
from src.application.use_cases.recurring_event_use_cases import RecurringEventUseCases
from src.domain.entities.account import AccountType
from src.domain.entities.financial_event import EventType
from src.domain.entities.purchase import PaymentMethod
from src.domain.entities.recurring_event import RecurrenceFrequency, RecurringEvent
from src.domain.services.recurring_event_service import RecurringEventService
from src.infrastructure.homebank.date_utils import date_to_julian
from src.infrastructure.homebank.mapping import (
    HB_ACCOUNT_TYPE_CREDITCARD, HB_PAYMODE_TRANSFER, OUR_ACCOUNT_TYPE_TO_HB,
    PAYMENT_METHOD_TO_HB_PAYMODE,
)
from src.infrastructure.homebank.xhb_models import (
    OF_INCOME, OF_SPLIT, HbAccount, HbCategory, HbCurrency, HbFav, HbFile, HbOperation, HbPayee,
)
from src.infrastructure.homebank.xhb_writer import XhbWriter

_FREQUENCY_TO_HB_UNIT = {
    RecurrenceFrequency.DAILY: 0,
    RecurrenceFrequency.WEEKLY: 1,
    RecurrenceFrequency.MONTHLY: 2,
    RecurrenceFrequency.YEARLY: 3,
}


class HomeBankExportUseCases:
    def __init__(
        self,
        account_use_cases: AccountUseCases,
        category_use_cases: CategoryUseCases,
        counterparty_use_cases: CounterpartyUseCases,
        credit_card_use_cases: CreditCardUseCases,
        financial_event_use_cases: FinancialEventUseCases,
        purchase_use_cases: PurchaseUseCases,
        recurring_event_use_cases: RecurringEventUseCases,
        writer: XhbWriter,
    ):
        self._account_use_cases = account_use_cases
        self._category_use_cases = category_use_cases
        self._counterparty_use_cases = counterparty_use_cases
        self._credit_card_use_cases = credit_card_use_cases
        self._financial_event_use_cases = financial_event_use_cases
        self._purchase_use_cases = purchase_use_cases
        self._recurring_event_use_cases = recurring_event_use_cases
        self._writer = writer
        self._recurring_service = RecurringEventService()

    def export(self, path: str, options: HomeBankExportOptionsDTO) -> HomeBankExportResultDTO:
        hb_file = HbFile(v="1.4", d="050402")
        counts: Dict[str, int] = {}

        accounts = self._account_use_cases.list_accounts()
        categories = self._category_use_cases.list_categories()
        counterparties = self._counterparty_use_cases.list_counterparties()
        credit_cards = self._credit_card_use_cases.list_cards() if options.include_credit_cards else []
        events = self._financial_event_use_cases.list_events(
            date_from=options.date_from, date_to=options.date_to,
        )

        currencies_used = sorted({e.currency for e in events} | {"BRL"})
        currency_key = {iso: i + 1 for i, iso in enumerate(currencies_used)}
        for iso, key in currency_key.items():
            hb_file.currencies.append(HbCurrency(key=key, iso=iso, name=iso, symb=iso))
        hb_file.curr = currency_key.get("BRL", 1)

        account_currency_counts: Dict[str, Dict[str, int]] = {}
        for e in events:
            for acc_id in filter(None, [e.account_id, e.destination_account_id]):
                counter = account_currency_counts.setdefault(acc_id, {})
                counter[e.currency] = counter.get(e.currency, 0) + 1

        key_counter = 1
        account_id_to_key: Dict[str, int] = {}
        for acc in accounts:
            key = key_counter
            key_counter += 1
            account_id_to_key[acc.id] = key
            hb_type = OUR_ACCOUNT_TYPE_TO_HB.get(AccountType(acc.type), 1)
            counter = account_currency_counts.get(acc.id, {})
            dominant_currency = max(counter, key=counter.get) if counter else "BRL"
            hb_file.accounts.append(HbAccount(
                key=key, pos=key, type=hb_type,
                curr=currency_key.get(dominant_currency, hb_file.curr),
                name=acc.name, initial=acc.initial_balance,
            ))
        counts["accounts"] = len(accounts)

        credit_card_id_to_key: Dict[str, int] = {}
        for card in credit_cards:
            key = key_counter
            key_counter += 1
            credit_card_id_to_key[card.id] = key
            hb_file.accounts.append(HbAccount(
                key=key, pos=key, type=HB_ACCOUNT_TYPE_CREDITCARD, curr=hb_file.curr,
                name=card.name, minimum=card.credit_limit, flags=0 if card.is_active else 2,
            ))
        counts["credit_cards"] = len(credit_cards)

        category_by_id = {c.id: c for c in categories}
        category_id_to_key: Dict[str, int] = {c.id: i + 1 for i, c in enumerate(categories)}

        def root_ancestor(category):
            seen = set()
            current = category
            while current.parent_id and current.parent_id in category_by_id and current.parent_id not in seen:
                seen.add(current.parent_id)
                current = category_by_id[current.parent_id]
            return current

        category_event_bias: Dict[str, Dict[str, int]] = {}
        for e in events:
            if e.category_id:
                counter = category_event_bias.setdefault(e.category_id, {"income": 0, "other": 0})
                if e.event_type in ("income", "refund"):
                    counter["income"] += 1
                else:
                    counter["other"] += 1

        for cat in categories:
            key = category_id_to_key[cat.id]
            parent_key = 0
            if cat.parent_id:
                parent = category_by_id.get(cat.parent_id)
                if parent is not None:
                    if parent.parent_id:
                        parent_key = category_id_to_key.get(root_ancestor(parent).id, 0)
                    else:
                        parent_key = category_id_to_key[parent.id]
            bias = category_event_bias.get(cat.id, {"income": 0, "other": 0})
            flags = OF_INCOME if bias["income"] > bias["other"] else 0
            hb_file.categories.append(HbCategory(key=key, parent=parent_key, flags=flags, name=cat.name))
        counts["categories"] = len(categories)

        counterparty_id_to_key: Dict[str, int] = {cp.id: i + 1 for i, cp in enumerate(counterparties)}
        for cp in counterparties:
            hb_file.payees.append(HbPayee(key=counterparty_id_to_key[cp.id], name=cp.name))
        counts["counterparties"] = len(counterparties)

        kxfer_counter = 1
        event_count = 0
        transfer_count = 0
        purchase_count = 0
        fallback_account_count = 0
        default_account_key = next(iter(account_id_to_key.values()), None)
        warnings = []

        for e in events:
            if e.event_type == "transfer":
                src_key = account_id_to_key.get(e.account_id)
                dst_key = account_id_to_key.get(e.destination_account_id)
                if src_key is None or dst_key is None:
                    continue
                jd = date_to_julian(e.event_date)
                k = kxfer_counter
                kxfer_counter += 1
                hb_file.operations.append(HbOperation(
                    date=jd, amount=-abs(e.amount), account=src_key, dst_account=dst_key,
                    paymode=HB_PAYMODE_TRANSFER, wording=e.description, kxfer=k,
                ))
                hb_file.operations.append(HbOperation(
                    date=jd, amount=abs(e.amount), account=dst_key, dst_account=src_key,
                    paymode=HB_PAYMODE_TRANSFER, wording=e.description, kxfer=k,
                ))
                transfer_count += 1
                continue

            purchase = self._purchase_use_cases.get_purchase_by_event(e.id)
            purchase_credit_card_id = purchase["purchase"].credit_card_id if purchase else None
            account_key = account_id_to_key.get(e.account_id)
            credit_card_key = (
                credit_card_id_to_key.get(e.credit_card_id)
                or credit_card_id_to_key.get(purchase_credit_card_id)
            )
            target_account_key = credit_card_key or account_key
            if target_account_key is None:
                # Purchases paid by cash/debit/PIX aren't linked to any account in
                # our domain model, but HomeBank requires every operation to
                # belong to one - fall back to the first account, if any.
                if default_account_key is None:
                    continue
                target_account_key = default_account_key
                fallback_account_count += 1

            jd = date_to_julian(e.event_date)
            payee_key = counterparty_id_to_key.get(e.counterparty_id, 0)
            base_amount = e.amount if e.event_type in ("income", "refund") else -e.amount
            wording = e.description
            if e.event_type not in ("income", "expense", "purchase"):
                wording = f"[{e.event_type}] {wording}"

            paymode = 0
            if purchase is not None:
                paymode = PAYMENT_METHOD_TO_HB_PAYMODE.get(
                    PaymentMethod(purchase["purchase"].payment_method), 0
                )
                purchase_count += 1

            if purchase is not None and purchase["items"]:
                items = purchase["items"]
                sign = -1 if base_amount < 0 else 1
                scat = "||".join(str(category_id_to_key.get(i.category_id, 0)) for i in items)
                samt = "||".join(f"{sign * abs(i.total_price):.2f}" for i in items)
                smem = "||".join(self._sanitize(i.name) for i in items)
                hb_file.operations.append(HbOperation(
                    date=jd, amount=base_amount, account=target_account_key, paymode=paymode,
                    flags=OF_SPLIT, payee=payee_key, wording=wording,
                    scat=scat, samt=samt, smem=smem,
                ))
            else:
                category_key = category_id_to_key.get(e.category_id, 0)
                hb_file.operations.append(HbOperation(
                    date=jd, amount=base_amount, account=target_account_key, paymode=paymode,
                    flags=(OF_INCOME if base_amount >= 0 else 0), payee=payee_key,
                    category=category_key, wording=wording,
                ))
            if purchase is None:
                event_count += 1

        counts["events"] = event_count
        counts["transfers"] = transfer_count
        counts["purchases"] = purchase_count

        if fallback_account_count and default_account_key is not None:
            fallback_name = next(a.name for a in accounts if account_id_to_key[a.id] == default_account_key)
            warnings.append(
                f"{fallback_account_count} purchase(s) with no linked account or credit card "
                f"were exported against '{fallback_name}' as a fallback - HomeBank requires "
                f"every transaction to belong to an account, but cash/debit/PIX purchases "
                f"aren't tied to one here."
            )

        recurring_count = 0
        if options.include_recurring:
            for i, r in enumerate(self._recurring_event_use_cases.list_recurring_events()):
                account_key = account_id_to_key.get(r.account_id) or credit_card_id_to_key.get(r.credit_card_id)
                if account_key is None:
                    continue
                dst_key = account_id_to_key.get(r.destination_account_id) or 0
                unit = _FREQUENCY_TO_HB_UNIT.get(RecurrenceFrequency(r.frequency), 2)
                limit = 0
                if r.end_date is not None:
                    limit = self._count_occurrences(r)
                amount = r.amount if r.event_type in ("income", "refund") else -r.amount
                hb_file.favs.append(HbFav(
                    key=i + 1, amount=amount, account=account_key, dst_account=dst_key,
                    paymode=0, payee=counterparty_id_to_key.get(r.counterparty_id, 0),
                    category=category_id_to_key.get(r.category_id, 0), wording=r.description,
                    nextdate=date_to_julian(r.start_date), every=r.interval, unit=unit, limit=limit,
                ))
                recurring_count += 1
        counts["recurring_events"] = recurring_count

        self._writer.write(hb_file, path)
        return HomeBankExportResultDTO(path=path, counts=counts, warnings=warnings)

    def _count_occurrences(self, r) -> int:
        entity = RecurringEvent(
            event_type=EventType(r.event_type),
            description=r.description,
            amount=r.amount,
            frequency=RecurrenceFrequency(r.frequency),
            start_date=r.start_date,
            interval=r.interval,
            day_of_month=r.day_of_month,
            weekday=r.weekday,
            month=r.month,
            end_date=r.end_date,
            is_active=r.is_active,
        )
        far_future = date(r.end_date.year + 1, 1, 1) if r.end_date else date(r.start_date.year + 50, 1, 1)
        return len(self._recurring_service.generate_occurrences(entity, entity.start_date, far_future))

    def _sanitize(self, text: Optional[str]) -> str:
        return (text or "").replace("||", "|")
