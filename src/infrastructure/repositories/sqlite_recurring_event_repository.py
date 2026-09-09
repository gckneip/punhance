import sqlite3
import uuid
from datetime import date
from typing import List, Optional

from src.domain.entities.financial_event import EventType
from src.domain.entities.recurring_event import RecurrenceFrequency, RecurringEvent
from src.domain.repositories.recurring_event_repository import RecurringEventRepository


class SQLiteRecurringEventRepository(RecurringEventRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, recurring_event: RecurringEvent, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO recurring_events
               (id, event_type, description, amount, frequency, interval, day_of_month, weekday, month,
                start_date, end_date, is_active, category_id, account_id, destination_account_id,
                credit_card_id, counterparty_id, currency, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                recurring_event.id,
                recurring_event.event_type.value,
                recurring_event.description,
                recurring_event.amount,
                recurring_event.frequency.value,
                recurring_event.interval,
                recurring_event.day_of_month,
                recurring_event.weekday,
                recurring_event.month,
                recurring_event.start_date.isoformat(),
                recurring_event.end_date.isoformat() if recurring_event.end_date else None,
                int(recurring_event.is_active),
                recurring_event.category_id,
                recurring_event.account_id,
                recurring_event.destination_account_id,
                recurring_event.credit_card_id,
                recurring_event.counterparty_id,
                recurring_event.currency,
                recurring_event.notes,
                recurring_event.created_at,
                recurring_event.updated_at,
            ),
        )
        if commit:
            self._conn.commit()

    def find_by_id(self, recurring_event_id: str) -> Optional[RecurringEvent]:
        cursor = self._conn.execute(
            "SELECT * FROM recurring_events WHERE id = ?", (recurring_event_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def find_all(self, is_active: Optional[bool] = None) -> List[RecurringEvent]:
        query = "SELECT * FROM recurring_events WHERE 1=1"
        params = []
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(int(is_active))
        query += " ORDER BY start_date DESC"
        cursor = self._conn.execute(query, params)
        return [self._row_to_entity(row) for row in cursor.fetchall()]

    def delete(self, recurring_event_id: str, commit: bool = True) -> None:
        self._conn.execute(
            "DELETE FROM recurring_event_skips WHERE recurring_event_id = ?", (recurring_event_id,)
        )
        self._conn.execute(
            "DELETE FROM recurring_events WHERE id = ?", (recurring_event_id,)
        )
        if commit:
            self._conn.commit()

    def save_skip(self, recurring_event_id: str, occurrence_date: date, commit: bool = True) -> None:
        self._conn.execute(
            """INSERT OR IGNORE INTO recurring_event_skips
               (id, recurring_event_id, occurrence_date, created_at)
               VALUES (?, ?, ?, ?)""",
            (str(uuid.uuid4()), recurring_event_id, occurrence_date.isoformat(), None),
        )
        if commit:
            self._conn.commit()

    def find_skips(self, recurring_event_id: str) -> List[date]:
        cursor = self._conn.execute(
            "SELECT occurrence_date FROM recurring_event_skips WHERE recurring_event_id = ?",
            (recurring_event_id,),
        )
        return [date.fromisoformat(row["occurrence_date"]) for row in cursor.fetchall()]

    def delete_skip(self, recurring_event_id: str, occurrence_date: date, commit: bool = True) -> None:
        self._conn.execute(
            "DELETE FROM recurring_event_skips WHERE recurring_event_id = ? AND occurrence_date = ?",
            (recurring_event_id, occurrence_date.isoformat()),
        )
        if commit:
            self._conn.commit()

    def _row_to_entity(self, row: sqlite3.Row) -> RecurringEvent:
        return RecurringEvent(
            id=row["id"],
            event_type=EventType(row["event_type"]),
            description=row["description"],
            amount=row["amount"],
            frequency=RecurrenceFrequency(row["frequency"]),
            interval=row["interval"],
            day_of_month=row["day_of_month"],
            weekday=row["weekday"],
            month=row["month"],
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
            is_active=bool(row["is_active"]),
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
