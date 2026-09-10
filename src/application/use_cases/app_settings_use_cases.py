from src.domain.entities.app_settings import NavigationStyle
from src.domain.entities.theme import DEFAULT_THEME_ID
from src.domain.repositories.app_settings_repository import AppSettingsRepository

NAVIGATION_STYLE_KEY = "navigation_style"
THEME_KEY = "current_theme"


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
