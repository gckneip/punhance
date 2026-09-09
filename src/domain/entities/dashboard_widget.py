import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class DashboardWidgetKind(Enum):
    GENERIC = "generic"
    BUILTIN = "builtin"


@dataclass
class DashboardWidget:
    kind: DashboardWidgetKind
    title: str
    grid_row: int
    grid_col: int
    grid_row_span: int = 1
    grid_col_span: int = 1
    sort_order: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    source_preset_id: Optional[str] = None
    dashboard_id: str = "default"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        now = datetime.now().isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
