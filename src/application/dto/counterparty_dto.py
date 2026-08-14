from dataclasses import dataclass


@dataclass
class CreateCounterpartyDTO:
    name: str


@dataclass
class CounterpartyDTO:
    id: str
    name: str
