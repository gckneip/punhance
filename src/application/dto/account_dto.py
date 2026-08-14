from dataclasses import dataclass


@dataclass
class CreateAccountDTO:
    name: str
    type: str
    initial_balance: float = 0.0


@dataclass
class AccountDTO:
    id: str
    name: str
    type: str
    initial_balance: float
