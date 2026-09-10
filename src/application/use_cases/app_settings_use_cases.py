from src.domain.entities.app_settings import NavigationStyle
from src.domain.repositories.app_settings_repository import AppSettingsRepository

NAVIGATION_STYLE_KEY = "navigation_style"


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
