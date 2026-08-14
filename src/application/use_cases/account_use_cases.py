from typing import List
from src.domain.entities.account import Account
from src.domain.repositories.account_repository import AccountRepository
from src.application.dto.account_dto import CreateAccountDTO, AccountDTO


class AccountUseCases:
    def __init__(self, account_repository: AccountRepository):
        self._account_repository = account_repository

    def create_account(self, dto: CreateAccountDTO) -> AccountDTO:
        account = Account(
            name=dto.name,
            type=dto.type,
            initial_balance=dto.initial_balance,
        )
        self._account_repository.save(account)
        return self._to_dto(account)

    def list_accounts(self) -> List[AccountDTO]:
        accounts = self._account_repository.find_all()
        return [self._to_dto(a) for a in accounts]

    def delete_account(self, account_id: str) -> None:
        self._account_repository.delete(account_id)

    def _to_dto(self, account: Account) -> AccountDTO:
        return AccountDTO(
            id=account.id,
            name=account.name,
            type=account.type,
            initial_balance=account.initial_balance,
        )
