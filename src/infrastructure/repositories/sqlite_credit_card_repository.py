import sqlite3
from typing import List, Optional
from src.domain.entities.credit_card import CreditCard
from src.domain.repositories.credit_card_repository import CreditCardRepository


class SQLiteCreditCardRepository(CreditCardRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, card: CreditCard) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO credit_cards
               (id, name, issuer, credit_limit, closing_day, due_day, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (card.id, card.name, card.issuer, card.credit_limit,
             card.closing_day, card.due_day, int(card.is_active)),
        )
        self._conn.commit()

    def find_by_id(self, card_id: str) -> Optional[CreditCard]:
        cursor = self._conn.execute(
            "SELECT * FROM credit_cards WHERE id = ?", (card_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_card(row)

    def find_all(self) -> List[CreditCard]:
        cursor = self._conn.execute(
            "SELECT * FROM credit_cards ORDER BY name"
        )
        return [self._row_to_card(row) for row in cursor.fetchall()]

    def delete(self, card_id: str) -> None:
        self._conn.execute("DELETE FROM credit_cards WHERE id = ?", (card_id,))
        self._conn.commit()

    def _row_to_card(self, row: sqlite3.Row) -> CreditCard:
        return CreditCard(
            id=row["id"],
            name=row["name"],
            issuer=row["issuer"],
            credit_limit=row["credit_limit"],
            closing_day=row["closing_day"],
            due_day=row["due_day"],
            is_active=bool(row["is_active"]),
        )
