from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CreateDashboardWidgetDTO:
    kind: str
    title: str
    grid_row: int
    grid_col: int
    grid_row_span: int = 1
    grid_col_span: int = 1
    sort_order: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    source_preset_id: Optional[str] = None
    dashboard_id: str = "default"


@dataclass
class DashboardWidgetDTO:
    id: str
    dashboard_id: str
    kind: str
    title: str
    grid_row: int
    grid_col: int
    grid_row_span: int
    grid_col_span: int
    sort_order: int
    config: Dict[str, Any]
    source_preset_id: Optional[str]


@dataclass
class DashboardWidgetLayoutUpdateDTO:
    id: str
    grid_row: int
    grid_col: int
    grid_row_span: int
    grid_col_span: int
    sort_order: int
