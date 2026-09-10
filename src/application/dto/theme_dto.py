from dataclasses import dataclass, field
from typing import List


@dataclass
class ThemeSummaryDTO:
    theme_id: str
    name: str
    is_custom: bool


@dataclass
class ThemeImportResultDTO:
    theme_id: str
    name: str
    warnings: List[str] = field(default_factory=list)
