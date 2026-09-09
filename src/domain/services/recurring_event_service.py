import calendar
from datetime import date, timedelta
from typing import Iterable, List, Set

from src.domain.entities.recurring_event import RecurrenceFrequency, RecurringEvent

MAX_ITERATIONS = 100_000


class RecurringEventService:
    def generate_occurrences(self, rule: RecurringEvent, date_from: date, date_to: date) -> List[date]:
        if not rule.is_active or rule.interval < 1:
            return []

        occurrences = []
        for i, occurrence_date in enumerate(self._iter_dates(rule)):
            if i >= MAX_ITERATIONS:
                break
            if rule.end_date is not None and occurrence_date > rule.end_date:
                break
            if occurrence_date >= date_to:
                break
            if occurrence_date >= date_from:
                occurrences.append(occurrence_date)
        return occurrences

    def compute_pending_occurrences(
        self,
        rule: RecurringEvent,
        date_from: date,
        date_to: date,
        confirmed_dates: Iterable[date],
        skipped_dates: Iterable[date],
    ) -> List[date]:
        excluded: Set[date] = set(confirmed_dates) | set(skipped_dates)
        return [d for d in self.generate_occurrences(rule, date_from, date_to) if d not in excluded]

    def _iter_dates(self, rule: RecurringEvent):
        if rule.frequency == RecurrenceFrequency.DAILY:
            yield from self._iter_daily(rule)
        elif rule.frequency == RecurrenceFrequency.WEEKLY:
            yield from self._iter_weekly(rule)
        elif rule.frequency == RecurrenceFrequency.MONTHLY:
            yield from self._iter_monthly(rule)
        elif rule.frequency == RecurrenceFrequency.YEARLY:
            yield from self._iter_yearly(rule)
        else:
            raise ValueError(f"Unsupported frequency: {rule.frequency}")

    def _iter_daily(self, rule: RecurringEvent):
        current = rule.start_date
        step = timedelta(days=rule.interval)
        while True:
            yield current
            current = current + step

    def _iter_weekly(self, rule: RecurringEvent):
        weekday = rule.weekday if rule.weekday is not None else rule.start_date.weekday()
        current = rule.start_date
        while current.weekday() != weekday:
            current += timedelta(days=1)
        step = timedelta(days=7 * rule.interval)
        while True:
            yield current
            current = current + step

    def _iter_monthly(self, rule: RecurringEvent):
        day_of_month = rule.day_of_month or rule.start_date.day
        k = 0
        while True:
            total_months = rule.start_date.month - 1 + k * rule.interval
            year = rule.start_date.year + total_months // 12
            month = total_months % 12 + 1
            max_day = calendar.monthrange(year, month)[1]
            occurrence = date(year, month, min(day_of_month, max_day))
            if occurrence >= rule.start_date:
                yield occurrence
            k += 1

    def _iter_yearly(self, rule: RecurringEvent):
        month = rule.month or rule.start_date.month
        day_of_month = rule.day_of_month or rule.start_date.day
        k = 0
        while True:
            year = rule.start_date.year + k * rule.interval
            max_day = calendar.monthrange(year, month)[1]
            occurrence = date(year, month, min(day_of_month, max_day))
            if occurrence >= rule.start_date:
                yield occurrence
            k += 1
