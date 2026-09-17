"""Application localization (i18n) runtime.

Mirrors the module-global, set-once-at-startup contract of
``src.presentation.theme``. Call :func:`load_language` exactly once in
``main()`` - after ``AppSettingsUseCases`` exists but before any widget is
constructed. Every read-site does ``from src.presentation import i18n`` (or
``from src.presentation.i18n import t``) and reads through it inside a function
body, so it naturally picks up the loaded language with zero per-file wiring.

Language changes apply on restart (same flow as theme/font), so there is no
live re-translation to worry about.
"""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate, QLocale

from src.presentation.translations import en as _en
from src.presentation.translations import es as _es
from src.presentation.translations import pt_BR as _pt_br

# Supported UI languages. Keys are the values persisted in app_settings.
SUPPORTED_LANGUAGES = ("en", "pt_BR", "es")
DEFAULT_LANGUAGE = "en"

_CATALOGS = {
    "en": _en.TRANSLATIONS,
    "pt_BR": _pt_br.TRANSLATIONS,
    "es": _es.TRANSLATIONS,
}

_QLOCALES = {
    "en": QLocale(QLocale.Language.English, QLocale.Country.UnitedStates),
    "pt_BR": QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil),
    "es": QLocale(QLocale.Language.Spanish, QLocale.Country.Spain),
}

# Currency code -> display symbol. Unknown codes fall back to the code itself.
CURRENCY_SYMBOLS = {
    "BRL": "R$",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "ARS": "$",
    "CAD": "$",
    "AUD": "$",
}

# Single source of truth for the currency picker (was duplicated across dialogs).
CURRENCIES = ["BRL", "USD", "EUR", "GBP", "JPY", "ARS", "CAD", "AUD"]

# --- module globals mutated by load_language() -----------------------------
_LANG = DEFAULT_LANGUAGE
_CATALOG = _CATALOGS[DEFAULT_LANGUAGE]
_QLOCALE = _QLOCALES[DEFAULT_LANGUAGE]


def load_language(lang: str) -> None:
    """Set the active UI language and Qt locale.

    Restart-only i18n: call once, in ``main()``, after ``AppSettingsUseCases``
    exists but before any widget/icon is constructed. Also sets the default
    ``QLocale`` so Qt input widgets (``QDateEdit``, ``QDoubleSpinBox`` /
    ``CurrencySpinBox``) inherit locale-correct separators and date formats
    automatically.
    """
    global _LANG, _CATALOG, _QLOCALE
    if lang not in _CATALOGS:
        lang = DEFAULT_LANGUAGE
    _LANG = lang
    _CATALOG = _CATALOGS[lang]
    _QLOCALE = _QLOCALES[lang]
    QLocale.setDefault(_QLOCALE)


def current_language() -> str:
    return _LANG


def detect_default_language() -> str:
    """Resolve a first-run default from the OS locale, falling back to English.

    Portuguese -> pt_BR, Spanish -> es, anything else -> en.
    """
    system = QLocale.system()
    language = system.language()
    if language == QLocale.Language.Portuguese:
        return "pt_BR"
    if language == QLocale.Language.Spanish:
        return "es"
    return DEFAULT_LANGUAGE


def t(key: str, **kwargs) -> str:
    """Look up a translation key, formatting with ``kwargs`` if provided.

    Falls back to the English catalog, then to the key itself, so a missing
    translation degrades gracefully instead of crashing.
    """
    template = _CATALOG.get(key)
    if template is None:
        template = _CATALOGS["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template
    return template


# --- formatting helpers ----------------------------------------------------

def _to_qdate(value) -> QDate:
    if isinstance(value, QDate):
        return value
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return QDate(value.year, value.month, value.day)
    raise TypeError(f"Unsupported date value: {value!r}")


def format_number(value, decimals: int = 2) -> str:
    """Format a number with the active locale's grouping/decimal separators."""
    return _QLOCALE.toString(float(value), "f", decimals)


def format_currency(value, currency_code: str = "BRL", decimals: int = 2) -> str:
    """Format a monetary amount: currency symbol + locale-formatted number.

    The record's currency is preserved (symbol from :data:`CURRENCY_SYMBOLS`);
    only the separators follow the active locale.
    """
    symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
    return f"{symbol} {format_number(value, decimals)}"


def format_date(value, style: str = "short") -> str:
    """Format a date for display in the active locale.

    ``style`` is ``"short"`` or ``"long"``. Use only for display - never for
    serialization (keep ``isoformat()`` for that).
    """
    qdate = _to_qdate(value)
    fmt = QLocale.FormatType.LongFormat if style == "long" else QLocale.FormatType.ShortFormat
    return _QLOCALE.toString(qdate, fmt)


def format_month_year(value) -> str:
    """Localized full month name + year, e.g. 'September 2026' / 'setembro de 2026'."""
    return _QLOCALE.toString(_to_qdate(value), "MMMM yyyy")


def format_weekday_date(value) -> str:
    """Localized weekday + date, e.g. 'Sunday, 13 Sep 2026'."""
    return _QLOCALE.toString(_to_qdate(value), "dddd, d MMM yyyy")


def format_day_month(value) -> str:
    """Localized short day + month, e.g. 'Sep 13' (used for week ranges)."""
    return _QLOCALE.toString(_to_qdate(value), "d MMM")


def locale_date_display_format() -> str:
    """Qt short-date format string for the active locale (for QDateEdit)."""
    return _QLOCALE.dateFormat(QLocale.FormatType.ShortFormat)


def weekday_abbr(python_weekday: int) -> str:
    """Localized short weekday name for a Python weekday index (Mon=0..Sun=6)."""
    # QLocale uses 1=Monday..7=Sunday.
    return _QLOCALE.dayName(python_weekday + 1, QLocale.FormatType.ShortFormat)
