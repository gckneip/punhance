import sqlite3
from typing import List, Optional
from src.domain.entities.portfolio_snapshot import PortfolioSnapshot
from src.domain.repositories.portfolio_snapshot_repository import PortfolioSnapshotRepository


class SQLitePortfolioSnapshotRepository(PortfolioSnapshotRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert(self, snapshot: PortfolioSnapshot) -> None:
        # Keyed by date (UNIQUE): repeated recordings on the same day replace
        # that day's row rather than pile up.
        self._conn.execute(
            """INSERT INTO portfolio_snapshots
               (id, date, total_invested, total_market_value, total_gain, total_income)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                 total_invested=excluded.total_invested,
                 total_market_value=excluded.total_market_value,
                 total_gain=excluded.total_gain,
                 total_income=excluded.total_income""",
            (
                snapshot.id,
                snapshot.date,
                snapshot.total_invested,
                snapshot.total_market_value,
                snapshot.total_gain,
                snapshot.total_income,
            ),
        )
        self._conn.commit()

    def find_all(self, since: Optional[str] = None) -> List[PortfolioSnapshot]:
        if since is not None:
            cursor = self._conn.execute(
                "SELECT * FROM portfolio_snapshots WHERE date >= ? ORDER BY date",
                (since,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY date"
            )
        return [self._row_to_snapshot(row) for row in cursor.fetchall()]

    def _row_to_snapshot(self, row: sqlite3.Row) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            id=row["id"],
            date=row["date"],
            total_invested=row["total_invested"],
            total_market_value=row["total_market_value"],
            total_gain=row["total_gain"],
            total_income=row["total_income"],
        )
