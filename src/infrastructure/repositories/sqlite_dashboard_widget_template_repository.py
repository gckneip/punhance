import json
import sqlite3
from datetime import datetime
from typing import List, Optional
from src.domain.entities.dashboard_widget_template import DashboardWidgetTemplate
from src.domain.repositories.dashboard_widget_template_repository import DashboardWidgetTemplateRepository


class SQLiteDashboardWidgetTemplateRepository(DashboardWidgetTemplateRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, template: DashboardWidgetTemplate) -> None:
        template.updated_at = datetime.now().isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO dashboard_widget_templates (
                id, title, config_json, row_span, col_span, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template.id,
                template.title,
                json.dumps(template.config),
                template.row_span,
                template.col_span,
                template.created_at,
                template.updated_at,
            ),
        )
        self._conn.commit()

    def find_by_id(self, template_id: str) -> Optional[DashboardWidgetTemplate]:
        cursor = self._conn.execute(
            "SELECT * FROM dashboard_widget_templates WHERE id = ?", (template_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._to_entity(row)

    def find_all(self) -> List[DashboardWidgetTemplate]:
        cursor = self._conn.execute(
            "SELECT * FROM dashboard_widget_templates ORDER BY created_at"
        )
        return [self._to_entity(row) for row in cursor.fetchall()]

    def delete(self, template_id: str) -> None:
        self._conn.execute(
            "DELETE FROM dashboard_widget_templates WHERE id = ?", (template_id,)
        )
        self._conn.commit()

    def _to_entity(self, row: sqlite3.Row) -> DashboardWidgetTemplate:
        return DashboardWidgetTemplate(
            id=row["id"],
            title=row["title"],
            config=json.loads(row["config_json"]) if row["config_json"] else {},
            row_span=row["row_span"],
            col_span=row["col_span"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
