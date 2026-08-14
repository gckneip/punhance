import sqlite3
from typing import List, Optional
from src.domain.entities.installment_plan import InstallmentPlan
from src.domain.repositories.installment_plan_repository import InstallmentPlanRepository


class SQLiteInstallmentPlanRepository(InstallmentPlanRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, plan: InstallmentPlan, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO installment_plans
               (id, purchase_id, total_amount, installment_count, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                plan.id,
                plan.purchase_id,
                plan.total_amount,
                plan.installment_count,
                plan.created_at,
            ),
        )
        if commit:
            self._conn.commit()

    def find_by_id(self, plan_id: str) -> Optional[InstallmentPlan]:
        cursor = self._conn.execute(
            "SELECT * FROM installment_plans WHERE id = ?", (plan_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_plan(row)

    def find_by_purchase(self, purchase_id: str) -> Optional[InstallmentPlan]:
        cursor = self._conn.execute(
            "SELECT * FROM installment_plans WHERE purchase_id = ?",
            (purchase_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_plan(row)

    def find_all(self) -> List[InstallmentPlan]:
        cursor = self._conn.execute(
            "SELECT * FROM installment_plans ORDER BY created_at DESC"
        )
        return [self._row_to_plan(row) for row in cursor.fetchall()]

    def delete(self, plan_id: str, commit: bool = True) -> None:
        self._conn.execute("DELETE FROM installment_plans WHERE id = ?", (plan_id,))
        if commit:
            self._conn.commit()

    def _row_to_plan(self, row: sqlite3.Row) -> InstallmentPlan:
        return InstallmentPlan(
            id=row["id"],
            purchase_id=row["purchase_id"],
            total_amount=row["total_amount"],
            installment_count=row["installment_count"],
            created_at=row["created_at"],
        )
