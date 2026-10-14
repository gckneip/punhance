from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.economic_indicator import IndicatorValue


class EconomicIndicatorRepository(ABC):
    @abstractmethod
    def save_many(self, values: List[IndicatorValue]) -> None:
        pass

    @abstractmethod
    def find_series(self, indicator_key: str, since: Optional[str] = None) -> List[IndicatorValue]:
        pass

    @abstractmethod
    def find_latest(self, indicator_key: str) -> Optional[IndicatorValue]:
        pass
