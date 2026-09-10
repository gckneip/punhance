from abc import ABC, abstractmethod
from typing import List


class ThemeRepository(ABC):
    @abstractmethod
    def list_builtin_keys(self) -> List[str]:
        pass

    @abstractmethod
    def read_builtin_json(self, key: str) -> str:
        pass

    @abstractmethod
    def list_custom_files(self) -> List[str]:
        pass

    @abstractmethod
    def read_custom_json(self, filename: str) -> str:
        pass

    @abstractmethod
    def save_custom_json(self, filename: str, raw_text: str) -> str:
        pass
