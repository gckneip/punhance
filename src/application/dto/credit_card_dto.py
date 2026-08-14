from dataclasses import dataclass


@dataclass
class CreateCreditCardDTO:
    name: str
    issuer: str
    credit_limit: float
    closing_day: int
    due_day: int
    is_active: bool = True


@dataclass
class CreditCardDTO:
    id: str
    name: str
    issuer: str
    credit_limit: float
    closing_day: int
    due_day: int
    is_active: bool
