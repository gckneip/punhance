from datetime import date, datetime
from typing import List, Optional

from src.application.dto.financial_event_dto import CreateFinancialEventDTO
from src.application.dto.recurring_event_dto import (
    CreateRecurringEventDTO, RecurringEventDTO, VirtualOccurrenceDTO,
)
from src.domain.entities.financial_event import FinancialEvent
from src.domain.entities.recurring_event import RecurringEvent
from src.domain.repositories.financial_event_repository import FinancialEventRepository
from src.domain.repositories.recurring_event_repository import RecurringEventRepository
from src.domain.services.recurring_event_service import RecurringEventService


class RecurringEventUseCases:
    def __init__(
        self,
        recurring_event_repository: RecurringEventRepository,
        financial_event_repository: FinancialEventRepository,
        recurring_event_service: RecurringEventService,
    ):
        self._repository = recurring_event_repository
        self._event_repository = financial_event_repository
        self._service = recurring_event_service

    def create_recurring_event(self, dto: CreateRecurringEventDTO) -> RecurringEventDTO:
        entity = RecurringEvent(
            event_type=dto.event_type,
            description=dto.description,
            amount=dto.amount,
            frequency=dto.frequency,
            start_date=dto.start_date,
            interval=dto.interval,
            day_of_month=dto.day_of_month,
            weekday=dto.weekday,
            month=dto.month,
            end_date=dto.end_date,
            is_active=dto.is_active,
            category_id=dto.category_id,
            account_id=dto.account_id,
            destination_account_id=dto.destination_account_id,
            credit_card_id=dto.credit_card_id,
            counterparty_id=dto.counterparty_id,
            currency=dto.currency,
            notes=dto.notes,
        )
        self._repository.save(entity)
        return self._to_dto(entity)

    def update_recurring_event(
        self, recurring_event_id: str, dto: CreateRecurringEventDTO
    ) -> Optional[RecurringEventDTO]:
        entity = self._repository.find_by_id(recurring_event_id)
        if entity is None:
            return None
        entity.event_type = dto.event_type
        entity.description = dto.description
        entity.amount = dto.amount
        entity.frequency = dto.frequency
        entity.start_date = dto.start_date
        entity.interval = dto.interval
        entity.day_of_month = dto.day_of_month
        entity.weekday = dto.weekday
        entity.month = dto.month
        entity.end_date = dto.end_date
        entity.is_active = dto.is_active
        entity.category_id = dto.category_id
        entity.account_id = dto.account_id
        entity.destination_account_id = dto.destination_account_id
        entity.credit_card_id = dto.credit_card_id
        entity.counterparty_id = dto.counterparty_id
        entity.currency = dto.currency
        entity.notes = dto.notes
        entity.updated_at = datetime.now().isoformat()
        self._repository.save(entity)
        return self._to_dto(entity)

    def delete_recurring_event(self, recurring_event_id: str) -> None:
        self._repository.delete(recurring_event_id)

    def list_recurring_events(self, is_active: Optional[bool] = None) -> List[RecurringEventDTO]:
        return [self._to_dto(e) for e in self._repository.find_all(is_active=is_active)]

    def get_pending_occurrences(
        self,
        date_from: date,
        date_to: date,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> List[VirtualOccurrenceDTO]:
        rules = self._repository.find_all(is_active=True)
        results: List[VirtualOccurrenceDTO] = []
        for rule in rules:
            if category_id and rule.category_id != category_id:
                continue
            if account_id and rule.account_id != account_id and rule.destination_account_id != account_id:
                continue
            if description and description.lower() not in rule.description.lower():
                continue

            confirmed = {
                e.event_date for e in self._event_repository.find_all(recurring_event_id=rule.id)
            }
            skipped = set(self._repository.find_skips(rule.id))
            pending_dates = self._service.compute_pending_occurrences(
                rule, date_from, date_to, confirmed, skipped
            )
            for occurrence_date in pending_dates:
                results.append(VirtualOccurrenceDTO(
                    recurring_event_id=rule.id,
                    occurrence_date=occurrence_date,
                    event_type=rule.event_type.value,
                    event_date=occurrence_date,
                    description=rule.description,
                    amount=rule.amount,
                    category_id=rule.category_id,
                    account_id=rule.account_id,
                    destination_account_id=rule.destination_account_id,
                    credit_card_id=rule.credit_card_id,
                    counterparty_id=rule.counterparty_id,
                    currency=rule.currency,
                    notes=rule.notes,
                ))
        results.sort(key=lambda o: o.occurrence_date)
        return results

    def confirm_occurrence(
        self, recurring_event_id: str, occurrence_date: date, dto: CreateFinancialEventDTO
    ) -> str:
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
            recurring_event_id=recurring_event_id,
        )
        self._event_repository.save(event)
        return event.id

    def skip_occurrence(self, recurring_event_id: str, occurrence_date: date) -> None:
        self._repository.save_skip(recurring_event_id, occurrence_date)

    def _to_dto(self, entity: RecurringEvent) -> RecurringEventDTO:
        return RecurringEventDTO(
            id=entity.id,
            event_type=entity.event_type.value,
            description=entity.description,
            amount=entity.amount,
            frequency=entity.frequency.value,
            interval=entity.interval,
            day_of_month=entity.day_of_month,
            weekday=entity.weekday,
            month=entity.month,
            start_date=entity.start_date,
            end_date=entity.end_date,
            is_active=entity.is_active,
            category_id=entity.category_id,
            account_id=entity.account_id,
            destination_account_id=entity.destination_account_id,
            credit_card_id=entity.credit_card_id,
            counterparty_id=entity.counterparty_id,
            currency=entity.currency,
            notes=entity.notes,
        )
