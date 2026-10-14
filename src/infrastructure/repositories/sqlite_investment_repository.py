import sqlite3
from typing import List, Optional
from src.domain.entities.investment import Investment, AssetType
from src.domain.repositories.investment_repository import InvestmentRepository


class SQLiteInvestmentRepository(InvestmentRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, investment: Investment) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO investments
               (id, name, asset_type, currency, ticker, account_id,
                current_price, price_updated_at, goal_amount, goal_date,
                yield_rate, yield_index, monthly_contribution, maturity_date, is_active, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                investment.id,
                investment.name,
                investment.asset_type.value,
                investment.currency,
                investment.ticker,
                investment.account_id,
                investment.current_price,
                investment.price_updated_at,
                investment.goal_amount,
                investment.goal_date,
                investment.yield_rate,
                investment.yield_index,
                investment.monthly_contribution,
                investment.maturity_date,
                int(investment.is_active),
                investment.notes,
            ),
        )
        self._conn.commit()

    def find_by_id(self, investment_id: str) -> Optional[Investment]:
        cursor = self._conn.execute(
            "SELECT * FROM investments WHERE id = ?", (investment_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_investment(row)

    def find_all(self) -> List[Investment]:
        cursor = self._conn.execute("SELECT * FROM investments ORDER BY name")
        return [self._row_to_investment(row) for row in cursor.fetchall()]

    def delete(self, investment_id: str) -> None:
        self._conn.execute("DELETE FROM investments WHERE id = ?", (investment_id,))
        self._conn.commit()

    def _row_to_investment(self, row: sqlite3.Row) -> Investment:
        return Investment(
            id=row["id"],
            name=row["name"],
            asset_type=AssetType(row["asset_type"]),
            currency=row["currency"],
            ticker=row["ticker"],
            account_id=row["account_id"],
            current_price=row["current_price"],
            price_updated_at=row["price_updated_at"],
            goal_amount=row["goal_amount"],
            goal_date=row["goal_date"],
            yield_rate=row["yield_rate"],
            yield_index=row["yield_index"],
            monthly_contribution=row["monthly_contribution"],
            maturity_date=row["maturity_date"],
            is_active=bool(row["is_active"]),
            notes=row["notes"],
        )
