"""Grocery shopping suggestions from past purchases.

This is deliberately a *statistical recurrence* engine, not a machine-learning
model: for each catalogued product it measures how often it has been bought and
in what quantity, predicts when it is next due, and proposes the items that fall
within the requested horizon (next week / next month). Every number it produces
is explainable ("you buy rice every ~26 days, last bought 24 days ago"), which
matters far more here than the marginal accuracy a heavier model might add.

The engine groups purchases strictly by ``product_id`` (catalogue entries);
free-text items without a linked product are ignored, since they cannot be
tracked across trips reliably.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median, pstdev, mean
from typing import Dict, List, Optional

from src.domain.repositories.purchase_repository import (
    PurchaseRepository, ProductPurchaseRecord,
)


# Horizon name -> look-ahead window in days. A product is suggested when its
# predicted next-purchase date falls on or before ``reference_date + window``.
HORIZON_DAYS: Dict[str, int] = {
    "weekly": 7,
    "monthly": 30,
}

# A product needs at least this many distinct shopping trips before we can
# estimate an interval at all (one interval needs two dates).
MIN_OCCURRENCES = 2


@dataclass
class ShoppingSuggestion:
    product_id: str
    typical_quantity: float          # median quantity per past trip
    unit: str
    estimated_unit_price: float      # most recent known unit price
    estimated_cost: float            # typical_quantity * estimated_unit_price
    avg_interval_days: float         # median gap between past trips
    occurrences: int                 # number of distinct trips observed
    last_purchase_date: date
    predicted_next_date: date
    days_until_due: int              # negative => already overdue
    confidence: str                  # "high" | "medium" | "low"
    cheapest_counterparty_id: Optional[str] = None
    cheapest_unit_price: Optional[float] = None


@dataclass
class ShoppingList:
    horizon: str
    reference_date: date
    items: List[ShoppingSuggestion] = field(default_factory=list)
    total_estimated_cost: float = 0.0


class ShoppingSuggestionService:
    def __init__(self, purchase_repository: PurchaseRepository):
        self._purchase_repo = purchase_repository

    def suggest(
        self,
        horizon: str = "monthly",
        reference_date: Optional[date] = None,
    ) -> ShoppingList:
        """Build a suggested shopping list for the given ``horizon``
        ("weekly" or "monthly"). ``reference_date`` defaults to today and is
        injectable so the result is deterministic under test."""
        if horizon not in HORIZON_DAYS:
            raise ValueError(
                f"Unknown horizon {horizon!r}; expected one of {sorted(HORIZON_DAYS)}"
            )
        window = HORIZON_DAYS[horizon]
        ref = reference_date or date.today()

        history = self._purchase_repo.find_product_purchase_history()
        by_product: Dict[str, List[ProductPurchaseRecord]] = {}
        for record in history:
            by_product.setdefault(record.product_id, []).append(record)

        suggestions: List[ShoppingSuggestion] = []
        for product_id, records in by_product.items():
            suggestion = self._build_suggestion(product_id, records, ref)
            if suggestion is None:
                continue
            if suggestion.days_until_due <= window:
                suggestions.append(suggestion)

        # Most overdue first; break ties by the pricier item so a quick glance
        # surfaces where the money goes.
        suggestions.sort(key=lambda s: (s.days_until_due, -s.estimated_cost))

        return ShoppingList(
            horizon=horizon,
            reference_date=ref,
            items=suggestions,
            total_estimated_cost=round(sum(s.estimated_cost for s in suggestions), 2),
        )

    def _build_suggestion(
        self,
        product_id: str,
        records: List[ProductPurchaseRecord],
        ref: date,
    ) -> Optional[ShoppingSuggestion]:
        # Collapse records to one "trip" per date: the same product may appear
        # as several line items in one purchase, or across purchases made the
        # same day. Each trip is what the user actually restocks in one go.
        trips: Dict[date, Dict[str, float]] = {}
        unit_counts: Dict[str, int] = {}
        for r in records:
            trip = trips.setdefault(r.event_date, {"quantity": 0.0, "total": 0.0})
            trip["quantity"] += r.quantity
            trip["total"] += r.total_price
            unit_counts[r.unit] = unit_counts.get(r.unit, 0) + 1

        trip_dates = sorted(trips)
        if len(trip_dates) < MIN_OCCURRENCES:
            return None

        intervals = [
            (trip_dates[i + 1] - trip_dates[i]).days
            for i in range(len(trip_dates) - 1)
        ]
        # Collapsing by date guarantees strictly increasing dates, so every
        # interval is >= 1; median is therefore >= 1 and the division below is
        # always safe.
        avg_interval = median(intervals)

        quantities = [trips[d]["quantity"] for d in trip_dates]
        typical_quantity = median(quantities)

        last_date = trip_dates[-1]
        last_trip = trips[last_date]
        # Most recent effective unit price (total / quantity for the last trip);
        # falls back to the last record's unit price if quantity is zero.
        if last_trip["quantity"]:
            estimated_unit_price = last_trip["total"] / last_trip["quantity"]
        else:
            estimated_unit_price = records[-1].unit_price

        predicted_next = last_date + timedelta(days=round(avg_interval))
        days_until_due = (predicted_next - ref).days

        cheapest_id, cheapest_price = self._cheapest_store(records)

        return ShoppingSuggestion(
            product_id=product_id,
            typical_quantity=typical_quantity,
            unit=max(unit_counts, key=unit_counts.get),
            estimated_unit_price=round(estimated_unit_price, 2),
            estimated_cost=round(typical_quantity * estimated_unit_price, 2),
            avg_interval_days=avg_interval,
            occurrences=len(trip_dates),
            last_purchase_date=last_date,
            predicted_next_date=predicted_next,
            days_until_due=days_until_due,
            confidence=self._confidence(intervals),
            cheapest_counterparty_id=cheapest_id,
            cheapest_unit_price=cheapest_price,
        )

    @staticmethod
    def _cheapest_store(records: List[ProductPurchaseRecord]):
        # Ignore non-positive prices: items entered with only a total (unit
        # price left at 0) would otherwise masquerade as the cheapest option.
        best_price: Optional[float] = None
        best_id: Optional[str] = None
        for r in records:
            if r.unit_price <= 0:
                continue
            if best_price is None or r.unit_price < best_price:
                best_price = r.unit_price
                best_id = r.counterparty_id
        if best_price is None:
            return None, None
        return best_id, round(best_price, 2)

    @staticmethod
    def _confidence(intervals: List[int]) -> str:
        """How regular the purchase cadence is. Many trips with a low spread of
        intervals => high confidence the prediction holds; few or erratic trips
        => low."""
        n = len(intervals) + 1  # number of trips
        avg = mean(intervals)
        # Coefficient of variation: spread relative to the mean interval.
        cv = (pstdev(intervals) / avg) if avg else 1.0
        if n >= 4 and cv < 0.5:
            return "high"
        if n >= 3 and cv < 0.9:
            return "medium"
        return "low"
