import sqlite3
from typing import List, Optional
from src.domain.entities.account import Account, AccountType
from src.domain.repositories.account_repository import AccountRepository


class SQLiteAccountRepository(AccountRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, account: Account) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO accounts (id, name, type, initial_balance) VALUES (?, ?, ?, ?)",
            (account.id, account.name, account.type.value, account.initial_balance),
        )
        self._conn.commit()

    def find_by_id(self, account_id: str) -> Optional[Account]:
        cursor = self._conn.execute(
            "SELECT id, name, type, initial_balance FROM accounts WHERE id = ?",
            (account_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Account(
            id=row["id"],
            name=row["name"],
            type=AccountType(row["type"]),
            initial_balance=row["initial_balance"],
        )

    def find_all(self) -> List[Account]:
        cursor = self._conn.execute(
            "SELECT id, name, type, initial_balance FROM accounts ORDER BY name"
        )
        return [
            Account(
                id=row["id"],
                name=row["name"],
                type=AccountType(row["type"]),
                initial_balance=row["initial_balance"],
            )
            for row in cursor.fetchall()
        ]

    def delete(self, account_id: str) -> None:
        self._conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        self._conn.commit()
