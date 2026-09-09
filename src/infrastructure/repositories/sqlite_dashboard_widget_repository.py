import json
import sqlite3
from datetime import datetime
from typing import List, Optional
from src.domain.entities.dashboard_widget import DashboardWidget, DashboardWidgetKind
from src.domain.repositories.dashboard_widget_repository import DashboardWidgetRepository


class SQLiteDashboardWidgetRepository(DashboardWidgetRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, widget: DashboardWidget) -> None:
        widget.updated_at = datetime.now().isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO dashboard_widgets (
                id, dashboard_id, kind, title, grid_row, grid_col,
                grid_row_span, grid_col_span, sort_order, config_json,
                source_preset_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                widget.id,
                widget.dashboard_id,
                widget.kind.value,
                widget.title,
                widget.grid_row,
                widget.grid_col,
                widget.grid_row_span,
                widget.grid_col_span,
                widget.sort_order,
                json.dumps(widget.config),
                widget.source_preset_id,
                widget.created_at,
                widget.updated_at,
            ),
        )
        self._conn.commit()

    def save_all(self, widgets: List[DashboardWidget]) -> None:
        for widget in widgets:
            self.save(widget)

    def find_by_id(self, widget_id: str) -> Optional[DashboardWidget]:
        cursor = self._conn.execute(
            "SELECT * FROM dashboard_widgets WHERE id = ?", (widget_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._to_entity(row)

    def find_all(self, dashboard_id: str = "default") -> List[DashboardWidget]:
        cursor = self._conn.execute(
            "SELECT * FROM dashboard_widgets WHERE dashboard_id = ? "
            "ORDER BY sort_order, grid_row, grid_col",
            (dashboard_id,),
        )
        return [self._to_entity(row) for row in cursor.fetchall()]

    def delete(self, widget_id: str) -> None:
        self._conn.execute(
            "DELETE FROM dashboard_widgets WHERE id = ?", (widget_id,)
        )
        self._conn.commit()

    def _to_entity(self, row: sqlite3.Row) -> DashboardWidget:
        return DashboardWidget(
            id=row["id"],
            dashboard_id=row["dashboard_id"],
            kind=DashboardWidgetKind(row["kind"]),
            title=row["title"],
            grid_row=row["grid_row"],
            grid_col=row["grid_col"],
            grid_row_span=row["grid_row_span"],
            grid_col_span=row["grid_col_span"],
            sort_order=row["sort_order"],
            config=json.loads(row["config_json"]) if row["config_json"] else {},
            source_preset_id=row["source_preset_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
