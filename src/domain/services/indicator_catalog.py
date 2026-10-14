from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class IndicatorInfo:
    """Presentation-facing metadata for a public economic indicator.

    The BCB SGS numeric series code lives in the infrastructure client
    (bcb_sgs_client.SERIES_CODES); the domain only knows the stable catalog key,
    how to label it, and how to format its value.
    """

    key: str
    label_key: str  # i18n key, e.g. "indicator.usd_brl"
    unit: str  # "currency" | "percent" | "index"
    decimals: int
    currency_code: str = "BRL"


# Ordered so the Market tab renders indicators predictably.
INDICATORS: Dict[str, IndicatorInfo] = {
    "usd_brl": IndicatorInfo("usd_brl", "indicator.usd_brl", "currency", 4, "BRL"),
    "selic": IndicatorInfo("selic", "indicator.selic", "percent", 2),
    "ipca": IndicatorInfo("ipca", "indicator.ipca", "percent", 2),
    "cdi": IndicatorInfo("cdi", "indicator.cdi", "percent", 2),
    "igpm": IndicatorInfo("igpm", "indicator.igpm", "percent", 2),
}


def all_keys() -> List[str]:
    return list(INDICATORS.keys())
