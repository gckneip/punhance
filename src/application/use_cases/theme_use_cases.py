import json
import os
from typing import List, Optional

from src.application.dto.theme_dto import ThemeImportResultDTO, ThemeSummaryDTO
from src.domain.entities.theme import (
    BUILTIN_PREFIX, BUILTIN_THEME_KEYS, CUSTOM_PREFIX, LIGHT_PALETTE, ThemePalette,
)
from src.domain.repositories.theme_repository import ThemeRepository
from src.infrastructure.theming.theme_parser import ThemeParseError, parse_theme_file, parse_theme_json


def _humanize(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").strip().title() or "Custom Theme"


def _palette_from_parsed(theme_id: str, name: str, parsed) -> ThemePalette:
    return ThemePalette(theme_id=theme_id, name=name, chart_categorical=parsed.chart_categorical, **parsed.colors)


class ThemeUseCases:
    def __init__(self, theme_repository: ThemeRepository):
        self._repository = theme_repository

    def list_available_themes(self) -> List[ThemeSummaryDTO]:
        themes: List[ThemeSummaryDTO] = []
        for key in BUILTIN_THEME_KEYS:
            if key == "light":
                themes.append(ThemeSummaryDTO(theme_id=f"{BUILTIN_PREFIX}light", name="Light", is_custom=False))
                continue
            try:
                raw = self._repository.read_builtin_json(key)
                parsed = parse_theme_json(raw, LIGHT_PALETTE, source_label=f"{key}.json")
            except (ThemeParseError, OSError):
                continue
            themes.append(ThemeSummaryDTO(
                theme_id=f"{BUILTIN_PREFIX}{key}",
                name=parsed.name or _humanize(key),
                is_custom=False,
            ))

        for filename in self._repository.list_custom_files():
            try:
                raw = self._repository.read_custom_json(filename)
                parsed = parse_theme_json(raw, LIGHT_PALETTE, source_label=filename)
            except (ThemeParseError, OSError):
                continue
            themes.append(ThemeSummaryDTO(
                theme_id=f"{CUSTOM_PREFIX}{filename}",
                name=parsed.name or _humanize(os.path.splitext(filename)[0]),
                is_custom=True,
            ))

        return themes

    def resolve_palette(self, theme_id: str) -> Optional[ThemePalette]:
        if not theme_id:
            return None
        if theme_id.startswith(BUILTIN_PREFIX):
            key = theme_id[len(BUILTIN_PREFIX):]
            if key == "light":
                return LIGHT_PALETTE
            try:
                raw = self._repository.read_builtin_json(key)
                parsed = parse_theme_json(raw, LIGHT_PALETTE, source_label=f"{key}.json")
            except (ThemeParseError, OSError):
                return None
            return _palette_from_parsed(theme_id, parsed.name or _humanize(key), parsed)

        if theme_id.startswith(CUSTOM_PREFIX):
            filename = theme_id[len(CUSTOM_PREFIX):]
            try:
                raw = self._repository.read_custom_json(filename)
                parsed = parse_theme_json(raw, LIGHT_PALETTE, source_label=filename)
            except (ThemeParseError, OSError):
                return None
            name = parsed.name or _humanize(os.path.splitext(filename)[0])
            return _palette_from_parsed(theme_id, name, parsed)

        return None

    def import_theme_file(self, source_path: str) -> ThemeImportResultDTO:
        parsed = parse_theme_file(source_path, LIGHT_PALETTE)
        name = parsed.name or _humanize(os.path.splitext(os.path.basename(source_path))[0])

        canonical = {
            "name": name,
            "base": "light",
            **parsed.colors,
            "chart_categorical": parsed.chart_categorical,
        }
        canonical_json = json.dumps(canonical, indent=2)

        original_filename = os.path.basename(source_path)
        final_filename = self._repository.save_custom_json(original_filename, canonical_json)

        return ThemeImportResultDTO(
            theme_id=f"{CUSTOM_PREFIX}{final_filename}",
            name=name,
            warnings=parsed.warnings,
        )
