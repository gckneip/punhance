import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.domain.entities.theme import ThemePalette

COLOR_KEYS = [
    "bg_app", "surface", "border", "text_primary", "text_secondary",
    "primary", "primary_hover", "primary_pressed", "income", "expense", "selection",
]
KNOWN_KEYS = set(COLOR_KEYS) | {"name", "base", "chart_categorical"}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
CHART_CATEGORICAL_LENGTH = 8


class ThemeParseError(ValueError):
    pass


@dataclass
class ParsedTheme:
    name: Optional[str]
    colors: dict
    chart_categorical: List[str]
    warnings: List[str] = field(default_factory=list)


def _is_valid_hex(value) -> bool:
    return isinstance(value, str) and bool(HEX_RE.match(value))


def parse_theme_json(raw_text: str, light_defaults: ThemePalette, source_label: str) -> ParsedTheme:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ThemeParseError(f"Invalid JSON in {source_label}: {exc}") from exc
    if not isinstance(data, dict):
        raise ThemeParseError(
            f"{source_label}: theme file must be a JSON object, not a {type(data).__name__}"
        )

    warnings: List[str] = []

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        warnings.append("`name` missing; defaulted to the file name")
        name = None
    else:
        name = name.strip()

    base = data.get("base", "light")
    if base != "light":
        warnings.append(f"`base` value {base!r} is not supported yet; used 'light'")

    colors = {}
    for key in COLOR_KEYS:
        default = getattr(light_defaults, key)
        if key not in data:
            warnings.append(f"`{key}` missing; defaulted to Light's value ({default})")
            colors[key] = default
        else:
            value = data[key]
            if not _is_valid_hex(value):
                warnings.append(
                    f"`{key}` ignored, invalid hex value {value!r}; defaulted to Light's value ({default})"
                )
                colors[key] = default
            else:
                colors[key] = value

    chart = data.get("chart_categorical")
    if "chart_categorical" not in data:
        warnings.append("`chart_categorical` missing; defaulted to Light's 8-color array")
        chart_final = list(light_defaults.chart_categorical)
    elif (
        not isinstance(chart, list)
        or len(chart) != CHART_CATEGORICAL_LENGTH
        or not all(_is_valid_hex(c) for c in chart)
    ):
        actual = len(chart) if isinstance(chart, list) else f"a {type(chart).__name__}"
        warnings.append(
            f"`chart_categorical` invalid (got {actual}, need exactly "
            f"{CHART_CATEGORICAL_LENGTH} valid hex colors); ignored entire array, "
            f"defaulted to Light's array"
        )
        chart_final = list(light_defaults.chart_categorical)
    else:
        chart_final = list(chart)

    for key in data.keys():
        if key not in KNOWN_KEYS:
            warnings.append(f"unknown key `{key}` ignored")

    return ParsedTheme(name=name, colors=colors, chart_categorical=chart_final, warnings=warnings)


def parse_theme_file(path: str, light_defaults: ThemePalette) -> ParsedTheme:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except OSError as exc:
        raise ThemeParseError(f"Could not read {path}: {exc}") from exc
    source_label = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return parse_theme_json(raw_text, light_defaults, source_label)
