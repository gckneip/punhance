import sqlite3
from typing import List, Optional
from src.domain.entities.counterparty import Counterparty
from src.domain.repositories.counterparty_repository import CounterpartyRepository


class SQLiteCounterpartyRepository(CounterpartyRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, counterparty: Counterparty) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO counterparties (id, name) VALUES (?, ?)",
            (counterparty.id, counterparty.name),
        )
        self._conn.commit()

    def find_by_id(self, counterparty_id: str) -> Optional[Counterparty]:
        cursor = self._conn.execute(
            "SELECT id, name FROM counterparties WHERE id = ?", (counterparty_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Counterparty(id=row["id"], name=row["name"])

    def find_all(self) -> List[Counterparty]:
        cursor = self._conn.execute(
            "SELECT id, name FROM counterparties ORDER BY name"
        )
        return [
            Counterparty(id=row["id"], name=row["name"]) for row in cursor.fetchall()
        ]

    def delete(self, counterparty_id: str) -> None:
        self._conn.execute(
            "DELETE FROM counterparties WHERE id = ?", (counterparty_id,)
        )
        self._conn.commit()
