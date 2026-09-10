from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


@dataclass
class HomeBankImportPlanDTO:
    counts: Dict[str, int]
    warnings: List[str]
    warnings_truncated: bool = False


@dataclass
class HomeBankImportResultDTO:
    created_counts: Dict[str, int]
    warnings: List[str]


@dataclass
class HomeBankExportOptionsDTO:
    include_credit_cards: bool = True
    include_recurring: bool = True
    date_from: Optional[date] = None
    date_to: Optional[date] = None


@dataclass
class HomeBankExportResultDTO:
    path: str
    counts: Dict[str, int]
    warnings: List[str] = field(default_factory=list)
