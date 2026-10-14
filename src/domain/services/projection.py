"""Pure projection math for investment yields — no I/O, easily testable.

All rates here are annual *fractions* (0.12 = 12% a.a.). Callers convert the
holding's stored yield_rate (a percentage number) + yield_index into an effective
annual fraction via effective_annual_rate(), then feed it to the projections.
"""
from typing import Optional


def effective_annual_rate(
    yield_rate: Optional[float],
    yield_index: str,
    cdi: Optional[float] = None,
    selic: Optional[float] = None,
    ipca_annual: Optional[float] = None,
) -> Optional[float]:
    """Resolve a holding's stored yield into an effective annual fraction.

    cdi/selic are the benchmarks' latest *annual %* (SGS 4389 / 432 are already
    annualized). ipca_annual is the annualized IPCA in %. Returns None when the
    needed benchmark isn't available (so callers can skip the projection).
    """
    if yield_rate is None:
        return None
    idx = yield_index or "prefixed"
    if idx == "prefixed":
        return yield_rate / 100.0
    if idx == "cdi":
        return None if cdi is None else (yield_rate / 100.0) * (cdi / 100.0)
    if idx == "selic":
        return None if selic is None else (yield_rate / 100.0) * (selic / 100.0)
    if idx == "ipca_plus":
        return None if ipca_annual is None else (ipca_annual / 100.0) + (yield_rate / 100.0)
    if idx == "selic_plus":
        return None if selic is None else (selic / 100.0) + (yield_rate / 100.0)
    if idx == "cdi_plus":
        return None if cdi is None else (cdi / 100.0) + (yield_rate / 100.0)
    return None


def monthly_rate(annual_fraction: float) -> float:
    """Compound-consistent monthly rate for an annual fraction."""
    return (1.0 + annual_fraction) ** (1.0 / 12.0) - 1.0


def annual_income(value: float, annual_fraction: float) -> float:
    return value * annual_fraction


def monthly_income(value: float, annual_fraction: float) -> float:
    return value * monthly_rate(annual_fraction)


def project_value(value: float, annual_fraction: float, months: int) -> float:
    return value * ((1.0 + annual_fraction) ** (months / 12.0))


def project_value_with_contributions(
    value: float, annual_fraction: float, monthly_contributions: list
) -> list:
    """Series of projected values (length len(monthly_contributions)+1), starting
    at `value`. Each step compounds by the monthly rate, then adds that month's
    scheduled contributions. monthly_contributions[m-1] is the total landing in
    month m."""
    rate = monthly_rate(annual_fraction) if annual_fraction else 0.0
    series = [value]
    current = value
    for contribution in monthly_contributions:
        current = current * (1.0 + rate) + contribution
        series.append(current)
    return series


def goal_eta_months(
    value: float,
    goal: float,
    annual_fraction: float,
    monthly_deposit: float = 0.0,
    max_months: int = 600,
) -> Optional[int]:
    """Months until `value` (compounding monthly, plus a monthly deposit) reaches
    `goal`. Returns 0 if already reached, None if unreachable within max_months."""
    if goal <= 0 or value >= goal:
        return 0 if value >= goal else None
    rate = monthly_rate(annual_fraction) if annual_fraction else 0.0
    if rate <= 0 and monthly_deposit <= 0:
        return None
    current = value
    for month in range(1, max_months + 1):
        current = current * (1.0 + rate) + monthly_deposit
        if current >= goal:
            return month
    return None
