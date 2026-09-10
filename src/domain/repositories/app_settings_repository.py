from abc import ABC, abstractmethod
from typing import Optional


class AppSettingsRepository(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        pass
