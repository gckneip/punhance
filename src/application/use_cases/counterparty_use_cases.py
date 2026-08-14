from typing import List
from src.domain.entities.counterparty import Counterparty
from src.domain.repositories.counterparty_repository import CounterpartyRepository
from src.application.dto.counterparty_dto import CreateCounterpartyDTO, CounterpartyDTO


class CounterpartyUseCases:
    def __init__(self, counterparty_repository: CounterpartyRepository):
        self._counterparty_repository = counterparty_repository

    def create_counterparty(self, dto: CreateCounterpartyDTO) -> CounterpartyDTO:
        entity = Counterparty(name=dto.name)
        self._counterparty_repository.save(entity)
        return self._to_dto(entity)

    def list_counterparties(self) -> List[CounterpartyDTO]:
        entities = self._counterparty_repository.find_all()
        return [self._to_dto(e) for e in entities]

    def delete_counterparty(self, counterparty_id: str) -> None:
        self._counterparty_repository.delete(counterparty_id)

    def _to_dto(self, entity: Counterparty) -> CounterpartyDTO:
        return CounterpartyDTO(id=entity.id, name=entity.name)
