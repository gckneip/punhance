from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.portfolio_snapshot import PortfolioSnapshot


class PortfolioSnapshotRepository(ABC):
    @abstractmethod
    def upsert(self, snapshot: PortfolioSnapshot) -> None:
        """Insert or replace the snapshot for its date (one row per day)."""
        pass

    @abstractmethod
    def find_all(self, since: Optional[str] = None) -> List[PortfolioSnapshot]:
        pass
