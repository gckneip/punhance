from dataclasses import dataclass


@dataclass
class IndicatorValue:
    """A single dated observation of a public economic indicator (cached from BCB)."""

    indicator_key: str  # catalog key, e.g. "usd_brl", "selic", "ipca"
    date: str  # ISO date string (YYYY-MM-DD)
    value: float
