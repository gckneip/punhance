from typing import List, Optional
from src.domain.entities.credit_card import CreditCard
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.repositories.credit_card_repository import CreditCardRepository
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.services.credit_card_service import CreditCardService
from src.application.dto.credit_card_dto import CreateCreditCardDTO, CreditCardDTO
from src.application.dto.card_payment_dto import CreateCardPaymentDTO


class CreditCardUseCases:
    def __init__(
        self,
        credit_card_repository: CreditCardRepository,
        credit_card_service: CreditCardService,
        financial_event_repository: FinancialEventRepository = None,
    ):
        self._repository = credit_card_repository
        self._service = credit_card_service
        self._event_repo = financial_event_repository

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

        # A card payment is a ledger entry - like a transfer from an account
        # to the card - that reduces the card's debt by the paid amount. It
        # is not tied to specific installments (see CreditCardService.get_status).
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

        return {"event_id": event.id}

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
