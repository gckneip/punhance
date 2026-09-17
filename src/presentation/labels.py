"""Localized display labels for domain enums.

The enum *values* stay in the database unchanged (English/machine strings); only
their on-screen display is translated. Each helper accepts either an enum member
or its raw ``.value`` string (render sites have both), and returns the localized
label, falling back to the raw value for anything unknown.
"""

from src.domain.entities.account import AccountType
from src.domain.entities.financial_event import EventType
from src.domain.entities.purchase import PaymentMethod
from src.domain.entities.recurring_event import RecurrenceFrequency
from src.domain.entities.installment import InstallmentStatus
from src.presentation.i18n import t


def _value(item):
    return item.value if hasattr(item, "value") else item


def account_type_label(item) -> str:
    return t(f"enum.account_type.{_value(item)}")


def event_type_label(item) -> str:
    return t(f"enum.event_type.{_value(item)}")


def payment_method_label(item) -> str:
    return t(f"enum.payment_method.{_value(item)}")


def recurrence_frequency_label(item) -> str:
    return t(f"enum.recurrence.{_value(item)}")


def installment_status_label(item) -> str:
    return t(f"enum.installment_status.{_value(item)}")


# Canonical English titles of the shipped default dashboard widgets / report,
# mapped to translation keys. Default layouts are seeded with these exact
# strings, so we can translate them at RENDER time (which also makes language
# switching work and covers databases seeded in English before i18n existed).
# A user who renames a widget gets custom text that won't match here and is
# shown verbatim, as intended.
_DEFAULT_TITLE_KEYS = {
    "Monthly Income": "dashboard.default.monthly_income",
    "Monthly Expenses": "dashboard.default.monthly_expenses",
    "Monthly Net": "dashboard.default.monthly_net",
    "Savings Rate": "builtin.savings_rate",
    "Recent Events": "dashboard.default.recent_events",
    "Future Transactions": "dashboard.default.future_transactions",
    "Quick Add": "builtin.quick_add",
    "Dashboard": "dashboard.default.report_name",
}


def localize_default_title(text, config=None) -> str:
    """Localize a stored dashboard widget/report title for display.

    Prefers an explicit ``config['title_key']`` if present; otherwise reverse-maps
    a known default English title to its translation. Custom titles pass through
    unchanged.
    """
    if config and config.get("title_key"):
        return t(config["title_key"])
    key = _DEFAULT_TITLE_KEYS.get(text)
    return t(key) if key else text


def account_type_choices():
    """(enum, label) pairs for populating an AccountType combo."""
    return [(m, account_type_label(m)) for m in AccountType]


def event_type_choices():
    return [(m, event_type_label(m)) for m in EventType]


def payment_method_choices():
    return [(m, payment_method_label(m)) for m in PaymentMethod]


def recurrence_frequency_choices():
    return [(m, recurrence_frequency_label(m)) for m in RecurrenceFrequency]
