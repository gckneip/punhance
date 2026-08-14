import sqlite3
from typing import List, Optional
from datetime import date
from src.domain.entities.financial_event import FinancialEvent, EventType
from src.domain.repositories.financial_event_repository import FinancialEventRepository


class SQLiteFinancialEventRepository(FinancialEventRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, event: FinancialEvent, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO financial_events
               (id, event_type, event_date, description, amount, category_id, account_id, destination_account_id, credit_card_id, counterparty_id, currency, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.event_type.value,
                event.event_date.isoformat(),
                event.description,
                event.amount,
                event.category_id,
                event.account_id,
                event.destination_account_id,
                event.credit_card_id,
                event.counterparty_id,
                event.currency,
                event.notes,
                event.created_at,
                event.updated_at,
            ),
        )
        if commit:
            self._conn.commit()

    def find_by_id(self, event_id: str) -> Optional[FinancialEvent]:
        cursor = self._conn.execute(
            "SELECT * FROM financial_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    def find_by_ids(self, event_ids: List[str]) -> List[FinancialEvent]:
        if not event_ids:
            return []
        unique_ids = list(dict.fromkeys(event_ids))
        placeholders = ",".join("?" * len(unique_ids))
        cursor = self._conn.execute(
            f"SELECT * FROM financial_events WHERE id IN ({placeholders})", unique_ids
        )
        return [self._row_to_event(row) for row in cursor.fetchall()]

    def find_all(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        event_type: Optional[EventType] = None,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
        destination_account_id: Optional[str] = None,
        counterparty_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> List[FinancialEvent]:
        query = "SELECT * FROM financial_events WHERE 1=1"
        params = []

        if date_from:
            query += " AND event_date >= ?"
            params.append(date_from.isoformat())
        if date_to:
            query += " AND event_date < ?"
            params.append(date_to.isoformat())
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        if category_id:
            query += " AND category_id = ?"
            params.append(category_id)
        if account_id:
            query += " AND (account_id = ? OR destination_account_id = ?)"
            params.append(account_id)
            params.append(account_id)
        if destination_account_id:
            query += " AND destination_account_id = ?"
            params.append(destination_account_id)
        if counterparty_id:
            query += " AND counterparty_id = ?"
            params.append(counterparty_id)
        if description:
            query += " AND description LIKE ?"
            params.append(f"%{description}%")

        query += " ORDER BY event_date DESC, created_at DESC"

        cursor = self._conn.execute(query, params)
        return [self._row_to_event(row) for row in cursor.fetchall()]

    def delete(self, event_id: str) -> None:
        self._conn.execute("DELETE FROM financial_events WHERE id = ?", (event_id,))
        self._conn.commit()

    def _row_to_event(self, row: sqlite3.Row) -> FinancialEvent:
        return FinancialEvent(
            id=row["id"],
            event_type=EventType(row["event_type"]),
            event_date=date.fromisoformat(row["event_date"]),
            description=row["description"],
            amount=row["amount"],
            category_id=row["category_id"],
            account_id=row["account_id"],
            destination_account_id=row["destination_account_id"],
            credit_card_id=row["credit_card_id"],
            counterparty_id=row["counterparty_id"],
            currency=row["currency"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
