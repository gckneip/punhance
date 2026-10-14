import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from typing import List

from src.domain.entities.economic_indicator import IndicatorValue
from src.infrastructure.config.settings import (
    BCB_SGS_BASE_URL,
    BCB_SGS_TIMEOUT_SECONDS,
)


# Catalog key -> BCB SGS numeric series code.
#   usd_brl : 1    (Dólar comercial - venda / PTAX)
#   selic   : 432  (Meta Selic definida pelo Copom, % a.a.)
#   ipca    : 433  (IPCA - variação mensal, %)
#   cdi     : 4389 (Taxa CDI acumulada no ano / anualizada, %)
#   igpm    : 189  (IGP-M - variação mensal, %)
SERIES_CODES = {
    "usd_brl": 1,
    "selic": 432,
    "ipca": 433,
    "cdi": 4389,
    "igpm": 189,
}

# How far back to query per indicator. Daily series use a shorter window (to keep
# the chart readable and the payload small); monthly series use several years so
# the chart still shows a meaningful number of points.
LOOKBACK_DAYS = {
    "usd_brl": 180,
    "selic": 365,
    "cdi": 180,
    "ipca": 365 * 5,
    "igpm": 365 * 5,
}
DEFAULT_LOOKBACK_DAYS = 365


class IndicatorFetchError(Exception):
    """Raised when an indicator cannot be fetched or parsed from BCB."""


class BcbSgsClient:
    """Fetches public economic indicators from the Banco Central do Brasil SGS API."""

    def __init__(self, retries: int = 3, backoff_seconds: float = 1.5):
        self._retries = retries
        self._backoff = backoff_seconds

    def fetch(self, indicator_key: str, today: date = None) -> List[IndicatorValue]:
        code = SERIES_CODES.get(indicator_key)
        if code is None:
            raise IndicatorFetchError(f"Unknown indicator '{indicator_key}'")

        end = today or date.today()
        lookback = LOOKBACK_DAYS.get(indicator_key, DEFAULT_LOOKBACK_DAYS)
        start = end - timedelta(days=lookback)
        url = BCB_SGS_BASE_URL.format(
            code=code,
            start=start.strftime("%d/%m/%Y"),
            end=end.strftime("%d/%m/%Y"),
        )
        payload = self._get_with_retries(url)

        try:
            raw = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise IndicatorFetchError(f"Invalid response: {exc}") from exc

        values: List[IndicatorValue] = []
        for item in raw:
            try:
                iso_date = _br_date_to_iso(item["data"])
                value = float(item["valor"])
            except (KeyError, ValueError, TypeError) as exc:
                raise IndicatorFetchError(f"Malformed data point: {exc}") from exc
            values.append(
                IndicatorValue(indicator_key=indicator_key, date=iso_date, value=value)
            )
        return values

    def _get_with_retries(self, url: str) -> str:
        """GET a URL, retrying transient failures. The BCB API is known to return
        sporadic HTTP 400s and timeouts under load, so retry those with a linear
        backoff before giving up."""
        last_exc = None
        for attempt in range(self._retries):
            try:
                request = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(
                    request, timeout=BCB_SGS_TIMEOUT_SECONDS
                ) as response:
                    return response.read().decode("utf-8")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                if attempt < self._retries - 1:
                    time.sleep(self._backoff * (attempt + 1))
        raise IndicatorFetchError(f"Network error: {last_exc}") from last_exc


def _br_date_to_iso(br_date: str) -> str:
    """Convert BCB's DD/MM/YYYY date string to ISO YYYY-MM-DD."""
    day, month, year = br_date.split("/")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
