import qtawesome as qta
from src.presentation import theme


def icon(name: str, color: str = None):
    return qta.icon(name, color=color or theme.TEXT_SECONDARY)
