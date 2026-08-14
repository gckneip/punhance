from typing import List, Optional
from datetime import date
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.application.dto.financial_event_dto import CreateFinancialEventDTO, FinancialEventDTO


class FinancialEventUseCases:
    def __init__(self, financial_event_repository: FinancialEventRepository):
        self._repository = financial_event_repository

    def create_event(self, dto: CreateFinancialEventDTO) -> FinancialEventDTO:
        event = FinancialEvent(
            event_type=dto.event_type,
            event_date=dto.event_date,
            description=dto.description,
            amount=dto.amount,
            category_id=dto.category_id,
            account_id=dto.account_id,
            destination_account_id=dto.destination_account_id,
            credit_card_id=dto.credit_card_id,
            counterparty_id=dto.counterparty_id,
            currency=dto.currency,
            notes=dto.notes,
        )
        self._repository.save(event)
        return self._to_dto(event)

    def list_events(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        event_type: Optional[EventType] = None,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
        destination_account_id: Optional[str] = None,
        counterparty_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> List[FinancialEventDTO]:
        events = self._repository.find_all(
            date_from=date_from,
            date_to=date_to,
            event_type=event_type,
            category_id=category_id,
            account_id=account_id,
            destination_account_id=destination_account_id,
            counterparty_id=counterparty_id,
            description=description,
        )
        return [self._to_dto(e) for e in events]

    def delete_event(self, event_id: str) -> None:
        self._repository.delete(event_id)

    def _to_dto(self, event: FinancialEvent) -> FinancialEventDTO:
        return FinancialEventDTO(
            id=event.id,
            event_type=event.event_type.value,
            event_date=event.event_date,
            description=event.description,
            amount=event.amount,
            category_id=event.category_id,
            account_id=event.account_id,
            destination_account_id=event.destination_account_id,
            credit_card_id=event.credit_card_id,
            counterparty_id=event.counterparty_id,
            currency=event.currency,
            notes=event.notes,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
