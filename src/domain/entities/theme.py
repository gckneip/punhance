from dataclasses import dataclass, field
from typing import List

BUILTIN_PREFIX = "builtin:"
CUSTOM_PREFIX = "custom:"
DEFAULT_THEME_ID = "builtin:light"

BUILTIN_THEME_KEYS = ["light", "dark", "solarized", "nord", "dracula"]


@dataclass
class ThemePalette:
    theme_id: str
    name: str
    bg_app: str
    surface: str
    border: str
    text_primary: str
    text_secondary: str
    primary: str
    primary_hover: str
    primary_pressed: str
    income: str
    expense: str
    selection: str
    chart_categorical: List[str] = field(default_factory=list)


# The permanent fallback/merge-base for every partial theme override. Defined
# here in pure Python (not as a bundled JSON preset) so it can never fail to
# load - every other theme, bundled or custom, is validated against this one.
LIGHT_PALETTE = ThemePalette(
    theme_id="builtin:light",
    name="Light",
    bg_app="#f4f6fb",
    surface="#ffffff",
    border="#e1e4eb",
    text_primary="#1f2430",
    text_secondary="#6b7280",
    primary="#3462eb",
    primary_hover="#2c53c9",
    primary_pressed="#2445a8",
    income="#1d9a6c",
    expense="#e5484d",
    selection="#dbe4ff",
    chart_categorical=[
        "#2a78d6", "#008300", "#e87ba4", "#eda100",
        "#1baf7a", "#eb6834", "#4a3aa7", "#e34948",
    ],
)
