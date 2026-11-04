"""Lightweight in-memory fake repositories for pure service unit tests.

These keep the summary/breakdown service tests focused on the aggregation logic
(no SQLite setup). Only the methods the services actually call are implemented.
"""
from datetime import date
from typing import List, Optional


class FakeEventRepo:
    def __init__(self, events):
        self._events = list(events)

    def find_all(self, date_from: Optional[date] = None, date_to: Optional[date] = None):
        # Mirrors the SQLite repo contract used by the services: date_to is the
        # exclusive upper bound (callers pass the first day of the next month).
        res = self._events
        if date_from is not None:
            res = [e for e in res if e.event_date >= date_from]
        if date_to is not None:
            res = [e for e in res if e.event_date < date_to]
        return list(res)


class FakeAccountRepo:
    def __init__(self, accounts):
        self._accounts = list(accounts)

    def find_all(self):
        return list(self._accounts)


class FakeCategoryRepo:
    def __init__(self, investment_ids=()):
        self._investment_ids = set(investment_ids)

    def find_investment_ids(self):
        return set(self._investment_ids)


class FakePurchaseRepo:
    """Maps a financial_event_id to a purchase and its items."""

    def __init__(self, by_event=None, items_by_purchase=None):
        self._by_event = by_event or {}
        self._items = items_by_purchase or {}

    def find_by_financial_event(self, event_id):
        return self._by_event.get(event_id)

    def find_items_by_purchase(self, purchase_id):
        return list(self._items.get(purchase_id, []))
