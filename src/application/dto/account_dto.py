from dataclasses import dataclass
from src.domain.entities.account import AccountType


@dataclass
class CreateAccountDTO:
    name: str
    type: AccountType
    initial_balance: float = 0.0


@dataclass
class AccountDTO:
    id: str
    name: str
    type: str
    initial_balance: float
