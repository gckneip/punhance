from src.domain.entities.app_settings import NavigationStyle
from src.domain.entities.theme import DEFAULT_THEME_ID
from src.domain.repositories.app_settings_repository import AppSettingsRepository

NAVIGATION_STYLE_KEY = "navigation_style"
THEME_KEY = "current_theme"
FONT_SIZE_KEY = "base_font_size"
DEFAULT_BASE_FONT_SIZE = 20  # mirrors src.presentation.theme.DEFAULT_BASE_FONT_SIZE
SIDEBAR_MODE_KEY = "sidebar_mode"
DEFAULT_SIDEBAR_MODE = "fixed"


class AppSettingsUseCases:
    def __init__(self, app_settings_repository: AppSettingsRepository):
        self._repository = app_settings_repository

    def get_navigation_style(self) -> NavigationStyle:
        raw = self._repository.get(NAVIGATION_STYLE_KEY)
        if raw is None:
            return NavigationStyle.TABS
        try:
            return NavigationStyle(raw)
        except ValueError:
            return NavigationStyle.TABS

    def set_navigation_style(self, style: NavigationStyle) -> None:
        self._repository.set(NAVIGATION_STYLE_KEY, style.value)

    def get_current_theme_id(self) -> str:
        return self._repository.get(THEME_KEY) or DEFAULT_THEME_ID

    def set_current_theme_id(self, theme_id: str) -> None:
        self._repository.set(THEME_KEY, theme_id)

    def get_base_font_size(self) -> int:
        raw = self._repository.get(FONT_SIZE_KEY)
        if raw is None:
            return DEFAULT_BASE_FONT_SIZE
        try:
            return int(raw)
        except ValueError:
            return DEFAULT_BASE_FONT_SIZE

    def set_base_font_size(self, size: int) -> None:
        self._repository.set(FONT_SIZE_KEY, str(size))

    def get_sidebar_mode(self) -> str:
        raw = self._repository.get(SIDEBAR_MODE_KEY)
        return raw if raw in ("fixed", "drawer") else DEFAULT_SIDEBAR_MODE

    def set_sidebar_mode(self, mode: str) -> None:
        self._repository.set(SIDEBAR_MODE_KEY, mode)
