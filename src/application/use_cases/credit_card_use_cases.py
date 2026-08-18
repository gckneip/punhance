from typing import List, Optional
from src.domain.entities.credit_card import CreditCard
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.repositories.credit_card_repository import CreditCardRepository
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.installment_repository import InstallmentRepository
from src.domain.services.credit_card_service import CreditCardService
from src.domain.entities.installment import InstallmentStatus
from src.application.dto.credit_card_dto import CreateCreditCardDTO, CreditCardDTO
from src.application.dto.card_payment_dto import CreateCardPaymentDTO


class CreditCardUseCases:
    def __init__(
        self,
        credit_card_repository: CreditCardRepository,
        credit_card_service: CreditCardService,
        financial_event_repository: FinancialEventRepository = None,
        installment_repository: InstallmentRepository = None,
    ):
        self._repository = credit_card_repository
        self._service = credit_card_service
        self._event_repo = financial_event_repository
        self._installment_repo = installment_repository

    def create_card(self, dto: CreateCreditCardDTO) -> CreditCardDTO:
        card = CreditCard(
            name=dto.name,
            issuer=dto.issuer,
            credit_limit=dto.credit_limit,
            closing_day=dto.closing_day,
            due_day=dto.due_day,
            is_active=dto.is_active,
        )
        self._repository.save(card)
        return self._to_dto(card)

    def update_card(self, card_id: str, dto: CreateCreditCardDTO) -> Optional[CreditCardDTO]:
        card = self._repository.find_by_id(card_id)
        if card is None:
            return None
        card.name = dto.name
        card.issuer = dto.issuer
        card.credit_limit = dto.credit_limit
        card.closing_day = dto.closing_day
        card.due_day = dto.due_day
        card.is_active = dto.is_active
        self._repository.save(card)
        return self._to_dto(card)

    def list_cards(self) -> List[CreditCardDTO]:
        return [self._to_dto(c) for c in self._repository.find_all()]

    def get_status(self, card_id: str):
        card = self._repository.find_by_id(card_id)
        if card is None:
            return None
        return self._service.get_status(card)

    def delete_card(self, card_id: str) -> None:
        self._repository.delete(card_id)

    def pay_card(self, dto: CreateCardPaymentDTO) -> dict:
        card = self._repository.find_by_id(dto.credit_card_id)
        if card is None:
            return {"error": "Credit card not found"}
        if not card.is_active:
            return {"error": "Credit card is not active"}

        payable_installments = []
        if dto.installment_ids and self._installment_repo:
            for inst_id in dto.installment_ids:
                inst = self._installment_repo.find_by_id(inst_id)
                if inst and inst.status in (InstallmentStatus.PENDING, InstallmentStatus.OVERDUE):
                    payable_installments.append(inst)

            expected_amount = round(sum(i.amount for i in payable_installments), 2)
            if abs(expected_amount - dto.amount) > 0.01:
                return {
                    "error": (
                        f"Payment amount (R$ {dto.amount:.2f}) does not match the sum "
                        f"of selected installments (R$ {expected_amount:.2f})"
                    )
                }

        event = FinancialEvent(
            event_type=EventType.CARD_PAYMENT,
            event_date=dto.event_date,
            description=dto.description,
            amount=dto.amount,
            account_id=dto.account_id,
            credit_card_id=dto.credit_card_id,
            notes=dto.notes,
        )
        self._event_repo.save(event)

        paid_count = 0
        for inst in payable_installments:
            inst.status = InstallmentStatus.PAID
            self._installment_repo.save(inst)
            paid_count += 1

        return {
            "event_id": event.id,
            "installments_paid": paid_count,
        }

    def _to_dto(self, card: CreditCard) -> CreditCardDTO:
        return CreditCardDTO(
            id=card.id,
            name=card.name,
            issuer=card.issuer,
            credit_limit=card.credit_limit,
            closing_day=card.closing_day,
            due_day=card.due_day,
            is_active=card.is_active,
        )
