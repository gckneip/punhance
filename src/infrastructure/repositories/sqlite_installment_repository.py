import sqlite3
from typing import List, Optional
from datetime import date
from src.domain.entities.installment import Installment, InstallmentStatus
from src.domain.repositories.installment_repository import InstallmentRepository


class SQLiteInstallmentRepository(InstallmentRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, installment: Installment, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO installments
               (id, installment_plan_id, installment_number, amount, due_date, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                installment.id,
                installment.installment_plan_id,
                installment.installment_number,
                installment.amount,
                installment.due_date.isoformat(),
                installment.status.value,
            ),
        )
        if commit:
            self._conn.commit()

    def save_all(self, installments: List[Installment], commit: bool = True) -> None:
        for inst in installments:
            self.save(inst, commit=False)
        if commit:
            self._conn.commit()

    def find_by_id(self, installment_id: str) -> Optional[Installment]:
        cursor = self._conn.execute(
            "SELECT * FROM installments WHERE id = ?", (installment_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_installment(row)

    def find_by_plan(self, plan_id: str) -> List[Installment]:
        cursor = self._conn.execute(
            "SELECT * FROM installments WHERE installment_plan_id = ? ORDER BY installment_number",
            (plan_id,),
        )
        return [self._row_to_installment(row) for row in cursor.fetchall()]

    def find_all(
        self,
        status: Optional[InstallmentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Installment]:
        query = "SELECT * FROM installments WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)
        if date_from:
            query += " AND due_date >= ?"
            params.append(date_from.isoformat())
        if date_to:
            query += " AND due_date < ?"
            params.append(date_to.isoformat())

        query += " ORDER BY due_date ASC, installment_number ASC"

        cursor = self._conn.execute(query, params)
        return [self._row_to_installment(row) for row in cursor.fetchall()]

    def find_by_credit_card(self, credit_card_id: str) -> List[Installment]:
        cursor = self._conn.execute(
            """SELECT i.* FROM installments i
               JOIN installment_plans ip ON i.installment_plan_id = ip.id
               JOIN purchases p ON ip.purchase_id = p.id
               WHERE p.credit_card_id = ?
               ORDER BY i.due_date ASC, i.installment_number ASC""",
            (credit_card_id,),
        )
        return [self._row_to_installment(row) for row in cursor.fetchall()]

    def delete(self, installment_id: str) -> None:
        self._conn.execute("DELETE FROM installments WHERE id = ?", (installment_id,))
        self._conn.commit()

    def delete_by_plan(self, plan_id: str, commit: bool = True) -> None:
        self._conn.execute(
            "DELETE FROM installments WHERE installment_plan_id = ?", (plan_id,)
        )
        if commit:
            self._conn.commit()

    def _row_to_installment(self, row: sqlite3.Row) -> Installment:
        return Installment(
            id=row["id"],
            installment_plan_id=row["installment_plan_id"],
            installment_number=row["installment_number"],
            amount=row["amount"],
            due_date=date.fromisoformat(row["due_date"]),
            status=InstallmentStatus(row["status"]),
        )
