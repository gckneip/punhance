import uuid
from dataclasses import dataclass, field
from enum import Enum


class AccountType(Enum):
    CASH = "Cash"
    CHECKING = "Checking Account"
    SAVINGS = "Savings Account"
    INVESTMENT = "Investment Account"
    VOUCHER = "Voucher"


@dataclass
class Account:
    name: str
    type: AccountType
    initial_balance: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
