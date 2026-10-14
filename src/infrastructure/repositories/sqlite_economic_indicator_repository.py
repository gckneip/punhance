import sqlite3
from typing import List, Optional
from src.domain.entities.economic_indicator import IndicatorValue
from src.domain.repositories.economic_indicator_repository import (
    EconomicIndicatorRepository,
)


class SQLiteEconomicIndicatorRepository(EconomicIndicatorRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_many(self, values: List[IndicatorValue]) -> None:
        self._conn.executemany(
            """INSERT OR REPLACE INTO economic_indicator_values
               (indicator_key, date, value) VALUES (?, ?, ?)""",
            [(v.indicator_key, v.date, v.value) for v in values],
        )
        self._conn.commit()

    def find_series(
        self, indicator_key: str, since: Optional[str] = None
    ) -> List[IndicatorValue]:
        if since is not None:
            cursor = self._conn.execute(
                "SELECT * FROM economic_indicator_values "
                "WHERE indicator_key = ? AND date >= ? ORDER BY date",
                (indicator_key, since),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM economic_indicator_values "
                "WHERE indicator_key = ? ORDER BY date",
                (indicator_key,),
            )
        return [self._row_to_value(row) for row in cursor.fetchall()]

    def find_latest(self, indicator_key: str) -> Optional[IndicatorValue]:
        cursor = self._conn.execute(
            "SELECT * FROM economic_indicator_values "
            "WHERE indicator_key = ? ORDER BY date DESC LIMIT 1",
            (indicator_key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_value(row)

    def _row_to_value(self, row: sqlite3.Row) -> IndicatorValue:
        return IndicatorValue(
            indicator_key=row["indicator_key"],
            date=row["date"],
            value=row["value"],
        )
