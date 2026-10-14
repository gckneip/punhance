from datetime import datetime
from typing import Dict, List, Optional

from src.domain.entities.economic_indicator import IndicatorValue
from src.domain.repositories.economic_indicator_repository import (
    EconomicIndicatorRepository,
)
from src.domain.repositories.app_settings_repository import AppSettingsRepository
from src.domain.services.indicator_catalog import all_keys
from src.infrastructure.market_data.bcb_sgs_client import BcbSgsClient, IndicatorFetchError

INDICATORS_LAST_FETCH_KEY = "indicators.last_fetch"


class IndicatorUseCases:
    def __init__(
        self,
        indicator_repository: EconomicIndicatorRepository,
        bcb_client: BcbSgsClient,
        app_settings_repository: AppSettingsRepository,
    ):
        self._repository = indicator_repository
        self._client = bcb_client
        self._settings = app_settings_repository

    def fetch_remote(self, keys: Optional[List[str]] = None) -> dict:
        """Fetch indicators from BCB over the network — NO database access.

        Safe to call from a worker thread (see IndicatorRefreshWorker): it only
        talks to the network, never to SQLite (whose connection is bound to the
        thread that created it). Returns
        {"fetched": {key: [IndicatorValue]}, "failed": {key: message}}.
        Persisting the result must happen on the main thread via store().
        """
        keys = keys or all_keys()
        fetched: Dict[str, List[IndicatorValue]] = {}
        failed: dict = {}
        for key in keys:
            try:
                values = self._client.fetch(key)
                if values:
                    fetched[key] = values
            except IndicatorFetchError as exc:
                failed[key] = str(exc)
        return {"fetched": fetched, "failed": failed}

    def store(self, fetched: Dict[str, List[IndicatorValue]]) -> List[str]:
        """Persist fetched indicator values and stamp the last-fetch time.

        Must run on the thread that owns the SQLite connection (the main thread).
        """
        updated: List[str] = []
        for key, values in (fetched or {}).items():
            if values:
                self._repository.save_many(values)
                updated.append(key)
        if updated:
            self._settings.set(
                INDICATORS_LAST_FETCH_KEY,
                datetime.now().isoformat(timespec="seconds"),
            )
        return updated

    def refresh(self, keys: Optional[List[str]] = None) -> dict:
        """Synchronous fetch + store (single-threaded callers only, e.g. tests).

        Returns {"updated": [...], "failed": {key: message}}. The threaded UI
        path uses fetch_remote() on the worker and store() on the main thread.
        """
        result = self.fetch_remote(keys)
        updated = self.store(result["fetched"])
        return {"updated": updated, "failed": result["failed"]}

    def get_latest(self, indicator_key: str) -> Optional[IndicatorValue]:
        return self._repository.find_latest(indicator_key)

    def get_series(
        self, indicator_key: str, since: Optional[str] = None
    ) -> List[IndicatorValue]:
        return self._repository.find_series(indicator_key, since=since)

    def get_last_fetch(self) -> Optional[str]:
        return self._settings.get(INDICATORS_LAST_FETCH_KEY)
