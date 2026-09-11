import sqlite3
from datetime import datetime
from typing import List, Optional
from src.domain.entities.dashboard_report import DashboardReport
from src.domain.repositories.dashboard_report_repository import DashboardReportRepository


class SQLiteDashboardReportRepository(DashboardReportRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, report: DashboardReport) -> None:
        report.updated_at = datetime.now().isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO dashboard_reports (
                id, name, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (report.id, report.name, report.sort_order, report.created_at, report.updated_at),
        )
        self._conn.commit()

    def save_all(self, reports: List[DashboardReport]) -> None:
        for report in reports:
            self.save(report)

    def find_by_id(self, report_id: str) -> Optional[DashboardReport]:
        cursor = self._conn.execute(
            "SELECT * FROM dashboard_reports WHERE id = ?", (report_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._to_entity(row)

    def find_all(self) -> List[DashboardReport]:
        cursor = self._conn.execute(
            "SELECT * FROM dashboard_reports ORDER BY sort_order, created_at"
        )
        return [self._to_entity(row) for row in cursor.fetchall()]

    def delete(self, report_id: str) -> None:
        self._conn.execute("DELETE FROM dashboard_reports WHERE id = ?", (report_id,))
        self._conn.commit()

    def _to_entity(self, row: sqlite3.Row) -> DashboardReport:
        return DashboardReport(
            id=row["id"],
            name=row["name"],
            sort_order=row["sort_order"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
