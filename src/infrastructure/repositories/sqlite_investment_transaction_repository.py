import sqlite3
from typing import List, Optional
from src.domain.entities.investment_transaction import (
    InvestmentTransaction,
    InvestmentTxnType,
)
from src.domain.repositories.investment_transaction_repository import (
    InvestmentTransactionRepository,
)


class SQLiteInvestmentTransactionRepository(InvestmentTransactionRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, transaction: InvestmentTransaction) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO investment_transactions
               (id, investment_id, txn_type, date, quantity, unit_price,
                fees, total, notes, financial_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                transaction.id,
                transaction.investment_id,
                transaction.txn_type.value,
                transaction.date,
                transaction.quantity,
                transaction.unit_price,
                transaction.fees,
                transaction.total,
                transaction.notes,
                transaction.financial_event_id,
            ),
        )
        self._conn.commit()

    def find_by_id(self, transaction_id: str) -> Optional[InvestmentTransaction]:
        cursor = self._conn.execute(
            "SELECT * FROM investment_transactions WHERE id = ?", (transaction_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_txn(row)

    def find_by_investment(self, investment_id: str) -> List[InvestmentTransaction]:
        cursor = self._conn.execute(
            "SELECT * FROM investment_transactions WHERE investment_id = ? "
            "ORDER BY date DESC",
            (investment_id,),
        )
        return [self._row_to_txn(row) for row in cursor.fetchall()]

    def delete(self, transaction_id: str) -> None:
        self._conn.execute(
            "DELETE FROM investment_transactions WHERE id = ?", (transaction_id,)
        )
        self._conn.commit()

    def delete_by_investment(self, investment_id: str) -> None:
        self._conn.execute(
            "DELETE FROM investment_transactions WHERE investment_id = ?",
            (investment_id,),
        )
        self._conn.commit()

    def find_by_financial_event(self, financial_event_id: str) -> Optional[InvestmentTransaction]:
        cursor = self._conn.execute(
            "SELECT * FROM investment_transactions WHERE financial_event_id = ?",
            (financial_event_id,),
        )
        row = cursor.fetchone()
        return self._row_to_txn(row) if row is not None else None

    def delete_by_financial_event(self, financial_event_id: str) -> None:
        self._conn.execute(
            "DELETE FROM investment_transactions WHERE financial_event_id = ?",
            (financial_event_id,),
        )
        self._conn.commit()

    def _row_to_txn(self, row: sqlite3.Row) -> InvestmentTransaction:
        keys = row.keys()
        return InvestmentTransaction(
            id=row["id"],
            investment_id=row["investment_id"],
            txn_type=InvestmentTxnType(row["txn_type"]),
            date=row["date"],
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            fees=row["fees"],
            total=row["total"],
            notes=row["notes"],
            financial_event_id=row["financial_event_id"] if "financial_event_id" in keys else None,
        )
