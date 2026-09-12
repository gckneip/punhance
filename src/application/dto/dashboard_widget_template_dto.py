from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CreateDashboardWidgetTemplateDTO:
    title: str
    config: Dict[str, Any] = field(default_factory=dict)
    row_span: int = 3
    col_span: int = 6


@dataclass
class DashboardWidgetTemplateDTO:
    id: str
    title: str
    config: Dict[str, Any]
    row_span: int
    col_span: int
