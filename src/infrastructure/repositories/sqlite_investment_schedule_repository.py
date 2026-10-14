import sqlite3
from typing import List, Optional
from src.domain.entities.investment_schedule import InvestmentSchedule, ScheduleFrequency
from src.domain.repositories.investment_schedule_repository import (
    InvestmentScheduleRepository,
)


class SQLiteInvestmentScheduleRepository(InvestmentScheduleRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save(self, schedule: InvestmentSchedule) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO investment_schedules
               (id, investment_id, amount, frequency, interval, start_date,
                end_date, last_generated_date, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                schedule.id,
                schedule.investment_id,
                schedule.amount,
                schedule.frequency.value,
                schedule.interval,
                schedule.start_date,
                schedule.end_date,
                schedule.last_generated_date,
                int(schedule.is_active),
            ),
        )
        self._conn.commit()

    def find_by_id(self, schedule_id: str) -> Optional[InvestmentSchedule]:
        cursor = self._conn.execute(
            "SELECT * FROM investment_schedules WHERE id = ?", (schedule_id,)
        )
        row = cursor.fetchone()
        return self._row_to_schedule(row) if row else None

    def find_by_investment(self, investment_id: str) -> List[InvestmentSchedule]:
        cursor = self._conn.execute(
            "SELECT * FROM investment_schedules WHERE investment_id = ? ORDER BY start_date",
            (investment_id,),
        )
        return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def find_all_active(self) -> List[InvestmentSchedule]:
        cursor = self._conn.execute(
            "SELECT * FROM investment_schedules WHERE is_active = 1"
        )
        return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def delete(self, schedule_id: str) -> None:
        self._conn.execute("DELETE FROM investment_schedules WHERE id = ?", (schedule_id,))
        self._conn.commit()

    def delete_by_investment(self, investment_id: str) -> None:
        self._conn.execute(
            "DELETE FROM investment_schedules WHERE investment_id = ?", (investment_id,)
        )
        self._conn.commit()

    def _row_to_schedule(self, row: sqlite3.Row) -> InvestmentSchedule:
        return InvestmentSchedule(
            id=row["id"],
            investment_id=row["investment_id"],
            amount=row["amount"],
            frequency=ScheduleFrequency(row["frequency"]),
            interval=row["interval"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            last_generated_date=row["last_generated_date"],
            is_active=bool(row["is_active"]),
        )
