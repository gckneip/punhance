import sqlite3
from typing import Optional

from src.domain.repositories.app_settings_repository import AppSettingsRepository


class SQLiteAppSettingsRepository(AppSettingsRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, key: str) -> Optional[str]:
        cursor = self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row["value"] if row is not None else None

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._conn.commit()
