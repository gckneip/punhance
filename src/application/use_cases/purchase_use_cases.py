import calendar
import sqlite3
from typing import Dict, List, Optional
from datetime import date, datetime
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.entities.purchase import Purchase, PaymentMethod
from src.domain.entities.purchase_item import PurchaseItem
from src.domain.entities.installment_plan import InstallmentPlan
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.purchase_repository import PurchaseRepository
from src.domain.repositories.installment_plan_repository import InstallmentPlanRepository
from src.domain.repositories.installment_repository import InstallmentRepository
from src.domain.services.installment_service import InstallmentService
from src.application.dto.purchase_dto import (
    CreatePurchaseDTO, PurchaseDTO, PurchaseItemDTO, InstallmentDTO,
)


def _add_one_month(d: date) -> date:
    if d.month == 12:
        year, month = d.year + 1, 1
    else:
        year, month = d.year, d.month + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def _derive_category_id(items) -> Optional[str]:
    category_ids = {i.category_id for i in items if i.category_id is not None}
    if len(category_ids) == 1:
        return category_ids.pop()
    return None


class PurchaseUseCases:
    def __init__(
        self,
        financial_event_repository: FinancialEventRepository,
        purchase_repository: PurchaseRepository,
        installment_plan_repository: InstallmentPlanRepository,
        installment_repository: InstallmentRepository,
        installment_service: InstallmentService,
        conn: sqlite3.Connection,
    ):
        self._event_repo = financial_event_repository
        self._purchase_repo = purchase_repository
        self._plan_repo = installment_plan_repository
        self._installment_repo = installment_repository
        self._installment_service = installment_service
        self._conn = conn

    def delete_purchase_by_event(self, financial_event_id: str) -> None:
        purchase = self._purchase_repo.find_by_financial_event(financial_event_id)
        if purchase is not None:
            self._purchase_repo.delete(purchase.id)

    def create_purchase(self, dto: CreatePurchaseDTO):
        try:
            category_id = _derive_category_id(dto.items) if dto.items else dto.category_id
            event = FinancialEvent(
                event_type=EventType.PURCHASE,
                event_date=dto.event_date,
                description=dto.description,
                amount=dto.total_amount,
                category_id=category_id,
                credit_card_id=dto.credit_card_id if dto.payment_method == PaymentMethod.CREDIT_CARD else None,
                counterparty_id=dto.counterparty_id,
                notes=dto.notes,
            )
            self._event_repo.save(event, commit=False)

            purchase = Purchase(
                financial_event_id=event.id,
                total_amount=dto.total_amount,
                payment_method=dto.payment_method,
                credit_card_id=dto.credit_card_id,
                counterparty_id=dto.counterparty_id,
                invoice_date=dto.event_date,
                notes=dto.notes,
            )
            self._purchase_repo.save(purchase, commit=False)

            installments = []
            warnings = []

            if dto.payment_method == PaymentMethod.CREDIT_CARD:
                plan = InstallmentPlan(
                    purchase_id=purchase.id,
                    total_amount=dto.total_amount,
                    installment_count=max(dto.installment_count, 1),
                    remainder_on_first=dto.remainder_on_first,
                )
                self._plan_repo.save(plan, commit=False)

                first_due_date = _add_one_month(event.event_date)

                generated = self._installment_service.create_installments(plan, first_due_date)
                self._installment_repo.save_all(generated, commit=False)
                installments = [self._installment_to_dto(i) for i in generated]

            items = []
            if dto.items:
                for item_dto in dto.items:
                    item = PurchaseItem(
                        purchase_id=purchase.id,
                        name=item_dto.name,
                        quantity=item_dto.quantity,
                        unit=item_dto.unit,
                        unit_price=item_dto.unit_price,
                        total_price=item_dto.total_price,
                        category_id=item_dto.category_id,
                    )
                    self._purchase_repo.save_item(item, commit=False)
                    items.append(item)

                items_total = round(sum(i.total_price for i in items), 2)
                diff = abs(items_total - dto.total_amount)
                if diff > 0.01:
                    warnings.append(
                        f"Item total (R$ {items_total:.2f}) differs from purchase total "
                        f"(R$ {dto.total_amount:.2f}) by R$ {diff:.2f}"
                    )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        return {
            "purchase_id": purchase.id,
            "financial_event_id": event.id,
            "installments": installments,
            "items": [self._item_to_dto(i) for i in items],
            "warnings": warnings,
        }

    def update_purchase(self, purchase_id: str, dto: CreatePurchaseDTO):
        purchase = self._purchase_repo.find_by_id(purchase_id)
        if purchase is None:
            return None

        warnings = []
        try:
            event = self._event_repo.find_by_id(purchase.financial_event_id)
            if event is not None:
                event.event_date = dto.event_date
                event.description = dto.description
                event.amount = dto.total_amount
                event.credit_card_id = dto.credit_card_id if dto.payment_method == PaymentMethod.CREDIT_CARD else None
                event.counterparty_id = dto.counterparty_id
                event.notes = dto.notes
                event.updated_at = datetime.now().isoformat()
                self._event_repo.save(event, commit=False)

            purchase.total_amount = dto.total_amount
            purchase.payment_method = dto.payment_method
            purchase.credit_card_id = dto.credit_card_id
            purchase.counterparty_id = dto.counterparty_id
            purchase.invoice_date = dto.event_date
            purchase.notes = dto.notes
            self._purchase_repo.save(purchase, commit=False)

            should_have_plan = dto.payment_method == PaymentMethod.CREDIT_CARD
            existing_plan = self._plan_repo.find_by_purchase(purchase.id)
            plan_changed = should_have_plan != (existing_plan is not None) or (
                existing_plan is not None and (
                    existing_plan.installment_count != dto.installment_count
                    or existing_plan.total_amount != dto.total_amount
                    or existing_plan.remainder_on_first != dto.remainder_on_first
                )
            )
            if existing_plan is not None and plan_changed:
                self._installment_repo.delete_by_plan(existing_plan.id, commit=False)
                self._plan_repo.delete(existing_plan.id, commit=False)

            if plan_changed and should_have_plan:
                new_plan = InstallmentPlan(
                    purchase_id=purchase.id,
                    total_amount=dto.total_amount,
                    installment_count=max(dto.installment_count, 1),
                    remainder_on_first=dto.remainder_on_first,
                )
                self._plan_repo.save(new_plan, commit=False)
                first_due_date = _add_one_month(dto.event_date)
                generated = self._installment_service.create_installments(new_plan, first_due_date)
                self._installment_repo.save_all(generated, commit=False)

            if dto.items:
                self._purchase_repo.delete_items_by_purchase(purchase.id, commit=False)
                items = []
                for item_dto in dto.items:
                    item = PurchaseItem(
                        purchase_id=purchase.id,
                        name=item_dto.name,
                        quantity=item_dto.quantity,
                        unit=item_dto.unit,
                        unit_price=item_dto.unit_price,
                        total_price=item_dto.total_price,
                        category_id=item_dto.category_id,
                    )
                    self._purchase_repo.save_item(item, commit=False)
                    items.append(item)

                items_total = round(sum(i.total_price for i in items), 2)
                diff = abs(items_total - dto.total_amount)
                if diff > 0.01:
                    warnings.append(
                        f"Item total (R$ {items_total:.2f}) differs from purchase total "
                        f"(R$ {dto.total_amount:.2f}) by R$ {diff:.2f}"
                    )

                if event is not None:
                    event.category_id = _derive_category_id(dto.items)
                    self._event_repo.save(event, commit=False)
            else:
                self._purchase_repo.delete_items_by_purchase(purchase.id, commit=False)
                if event is not None:
                    event.category_id = dto.category_id
                    self._event_repo.save(event, commit=False)

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        return {
            "purchase_id": purchase.id,
            "financial_event_id": purchase.financial_event_id,
            "warnings": warnings,
        }

    def list_purchases(self) -> List[PurchaseDTO]:
        purchases = self._purchase_repo.find_all()
        events_by_id = {
            e.id: e for e in self._event_repo.find_by_ids(
                [p.financial_event_id for p in purchases]
            )
        }
        result = []
        for p in purchases:
            event = events_by_id.get(p.financial_event_id)
            result.append(PurchaseDTO(
                id=p.id,
                financial_event_id=p.financial_event_id,
                total_amount=p.total_amount,
                payment_method=p.payment_method.value,
                credit_card_id=p.credit_card_id,
                counterparty_id=p.counterparty_id,
                invoice_date=p.invoice_date,
                notes=p.notes or (event.notes if event else None),
                event_date=event.event_date if event else None,
                description=event.description if event else None,
            ))
        return result

    def get_multi_category_event_ids(self) -> set:
        result = set()
        for p in self._purchase_repo.find_all():
            items = self._purchase_repo.find_items_by_purchase(p.id)
            category_ids = {i.category_id for i in items if i.category_id is not None}
            if len(category_ids) > 1:
                result.add(p.financial_event_id)
        return result

    def get_multi_installment_map(self) -> Dict[str, List[InstallmentDTO]]:
        plans = self._plan_repo.find_all()
        multi_plans = {p.id: p for p in plans if p.installment_count >= 2}
        if not multi_plans:
            return {}

        installments_by_plan: Dict[str, list] = {}
        for inst in self._installment_repo.find_all():
            if inst.installment_plan_id in multi_plans:
                installments_by_plan.setdefault(inst.installment_plan_id, []).append(inst)

        purchases_by_id = {p.id: p for p in self._purchase_repo.find_all()}

        result: Dict[str, List[InstallmentDTO]] = {}
        for plan_id, plan in multi_plans.items():
            purchase = purchases_by_id.get(plan.purchase_id)
            insts = installments_by_plan.get(plan_id)
            if purchase is None or not insts:
                continue
            result[purchase.financial_event_id] = [self._installment_to_dto(i) for i in insts]
        return result

    def get_purchase_by_event(self, financial_event_id: str):
        purchase = self._purchase_repo.find_by_financial_event(financial_event_id)
        if purchase is None:
            return None
        return self.get_purchase(purchase.id)

    def get_purchase(self, purchase_id: str):
        purchase = self._purchase_repo.find_by_id(purchase_id)
        if purchase is None:
            return None
        event = self._event_repo.find_by_id(purchase.financial_event_id)

        items = self._purchase_repo.find_items_by_purchase(purchase.id)

        plan = self._plan_repo.find_by_purchase(purchase.id)
        installments = []
        if plan:
            inst_list = self._installment_repo.find_by_plan(plan.id)
            installments = [self._installment_to_dto(i) for i in inst_list]

        return {
            "purchase": PurchaseDTO(
                id=purchase.id, financial_event_id=purchase.financial_event_id,
                total_amount=purchase.total_amount,
                payment_method=purchase.payment_method.value,
                credit_card_id=purchase.credit_card_id,
                counterparty_id=purchase.counterparty_id,
                invoice_date=purchase.invoice_date,
                notes=purchase.notes or (event.notes if event else None),
                event_date=event.event_date if event else None,
                description=event.description if event else None,
            ),
            "event_type": event.event_type.value if event else None,
            "category_id": event.category_id if event else None,
            "items": [self._item_to_dto(i) for i in items],
            "installments": installments,
            "remainder_on_first": plan.remainder_on_first if plan else False,
        }

    def _item_to_dto(self, item: PurchaseItem) -> PurchaseItemDTO:
        return PurchaseItemDTO(
            id=item.id,
            purchase_id=item.purchase_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            total_price=item.total_price,
            category_id=item.category_id,
        )

    def _installment_to_dto(self, inst) -> InstallmentDTO:
        return InstallmentDTO(
            id=inst.id,
            installment_plan_id=inst.installment_plan_id,
            installment_number=inst.installment_number,
            amount=inst.amount,
            due_date=inst.due_date,
            status=inst.status.value,
        )
