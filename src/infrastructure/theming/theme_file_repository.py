import re
from importlib import resources
from pathlib import Path
from typing import List

from src.domain.repositories.theme_repository import ThemeRepository

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class FileThemeRepository(ThemeRepository):
    def __init__(self, themes_dir: Path):
        self._themes_dir = themes_dir

    def list_builtin_keys(self) -> List[str]:
        keys = []
        preset_files = resources.files("src.infrastructure.theming.presets")
        for entry in preset_files.iterdir():
            if entry.name.endswith(".json"):
                keys.append(entry.name[: -len(".json")])
        return sorted(keys)

    def read_builtin_json(self, key: str) -> str:
        preset_files = resources.files("src.infrastructure.theming.presets")
        return preset_files.joinpath(f"{key}.json").read_text(encoding="utf-8")

    def list_custom_files(self) -> List[str]:
        if not self._themes_dir.exists():
            return []
        return sorted(p.name for p in self._themes_dir.glob("*.json") if p.is_file())

    def read_custom_json(self, filename: str) -> str:
        return (self._themes_dir / filename).read_text(encoding="utf-8")

    def save_custom_json(self, filename: str, raw_text: str) -> str:
        self._themes_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(filename).stem or "theme"
        base_name = _SAFE_NAME_RE.sub("-", base_name).strip("-.") or "theme"

        candidate = f"{base_name}.json"
        counter = 2
        while (self._themes_dir / candidate).exists():
            candidate = f"{base_name}-{counter}.json"
            counter += 1

        (self._themes_dir / candidate).write_text(raw_text, encoding="utf-8")
        return candidate
