from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from src.domain.services.indicator_catalog import INDICATORS, IndicatorInfo
from src.domain.services import projection
from src.domain.services import investment_schedule_service as sched_service
from src.domain.services.investment_chart_types import (
    AllocationDimension, HoldingMetric, PortfolioMetric, PORTFOLIO_VALUE_METRICS,
)


def _add_months(base: date, months: int) -> date:
    total = base.month - 1 + months
    year = base.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


class InvestmentChartDataService:
    """Turns investment/indicator/snapshot data into the (labels, series) shape
    that ChartWidget/PieChartWidget consume, plus stat values and table rows.

    Returns raw keys/values; the presentation layer localizes labels.
    """

    def __init__(self, investment_use_cases, indicator_use_cases, portfolio_snapshot_repository=None):
        self._investments = investment_use_cases
        self._indicators = indicator_use_cases
        self._snapshots = portfolio_snapshot_repository

    # -- portfolio ------------------------------------------------------------

    def get_portfolio_stat(self, metric: PortfolioMetric) -> float:
        summary = self._investments.get_portfolio_summary()
        return float(getattr(summary, metric.value, 0.0))

    def get_portfolio_value_series(self) -> Tuple[List[str], Dict[str, List[float]]]:
        """(dates, {metric_value: [values]}) from portfolio snapshots."""
        if self._snapshots is None:
            return [], {}
        snapshots = self._snapshots.find_all()
        if not snapshots:
            return [], {}
        dates = [s.date for s in snapshots]
        series = {
            metric.value: [float(getattr(s, metric.value, 0.0)) for s in snapshots]
            for metric in PORTFOLIO_VALUE_METRICS
        }
        return dates, series

    # -- allocation / holdings ------------------------------------------------

    def get_allocation(
        self, dimension: AllocationDimension, metric: HoldingMetric
    ) -> Tuple[List[str], List[float]]:
        """Sum a metric across holdings grouped by a dimension. Labels are raw
        keys (asset_type value or currency code); the renderer localizes them."""
        totals: Dict[str, float] = {}
        for inv in self._investments.list_investments():
            if dimension == AllocationDimension.CURRENCY:
                key = inv.currency
            else:
                key = inv.asset_type.value
            totals[key] = totals.get(key, 0.0) + float(getattr(inv, metric.value, 0.0))
        # Stable order by descending magnitude for readable pies/bars.
        items = sorted(totals.items(), key=lambda kv: abs(kv[1]), reverse=True)
        return [k for k, _ in items], [v for _, v in items]

    def get_holdings_breakdown(
        self, metric: HoldingMetric, top_n: Optional[int] = None
    ) -> Tuple[List[str], List[float]]:
        rows = [
            (inv.name, float(getattr(inv, metric.value, 0.0)))
            for inv in self._investments.list_investments()
        ]
        rows.sort(key=lambda nv: abs(nv[1]), reverse=True)
        if top_n:
            rows = rows[:top_n]
        return [n for n, _ in rows], [v for _, v in rows]

    def get_holdings(self) -> list:
        """Raw InvestmentDTO list for a holdings table widget."""
        return self._investments.list_investments()

    def get_savings_goals(self) -> List[dict]:
        """Savings boxes (Caixinha/Cofrinho) that have a goal, with progress + ETA.

        Returns dicts {name, current, goal, goal_date, pct, remaining, currency,
        eta_months, eta_date} ordered by descending completion. ETA uses the box's
        yield + planned monthly_contribution (None when unreachable/no data).
        """
        from src.domain.entities.investment import AssetType

        rows = []
        for inv in self._investments.list_investments():
            if inv.asset_type != AssetType.SAVINGS_BOX or not inv.goal_amount:
                continue
            pct = inv.market_value / inv.goal_amount * 100.0 if inv.goal_amount else 0.0
            rate = self._effective_rate(inv) or 0.0
            eta_months = projection.goal_eta_months(
                inv.market_value, inv.goal_amount, rate,
                monthly_deposit=inv.monthly_contribution or 0.0,
            )
            eta_date = _add_months(date.today(), eta_months).isoformat() if eta_months else None
            rows.append({
                "name": inv.name,
                "current": inv.market_value,
                "goal": inv.goal_amount,
                "goal_date": inv.goal_date,
                "pct": pct,
                "remaining": max(inv.goal_amount - inv.market_value, 0.0),
                "currency": inv.currency,
                "eta_months": eta_months,
                "eta_date": eta_date,
            })
        rows.sort(key=lambda r: r["pct"], reverse=True)
        return rows

    # -- yield / projections --------------------------------------------------

    def _ipca_annual(self) -> Optional[float]:
        """Annualized IPCA (%) by compounding the last 12 monthly readings."""
        series = self._indicators.get_series("ipca")
        if not series:
            return None
        recent = series[-12:]
        factor = 1.0
        for v in recent:
            factor *= (1.0 + v.value / 100.0)
        return (factor - 1.0) * 100.0

    def _benchmarks(self) -> dict:
        cdi = self._indicators.get_latest("cdi")
        selic = self._indicators.get_latest("selic")
        return {
            "cdi": cdi.value if cdi else None,
            "selic": selic.value if selic else None,
            "ipca_annual": self._ipca_annual(),
        }

    def _effective_rate(self, inv) -> Optional[float]:
        b = self._benchmarks()
        return projection.effective_annual_rate(
            inv.yield_rate, inv.yield_index,
            cdi=b["cdi"], selic=b["selic"], ipca_annual=b["ipca_annual"],
        )

    def get_income_projections(self) -> List[dict]:
        """Per-holding projected income for holdings with a resolvable yield."""
        rows = []
        for inv in self._investments.list_investments():
            rate = self._effective_rate(inv)
            if rate is None or inv.market_value <= 0:
                continue
            # Scheduled contributions (recurring deposits) landing over the next
            # 12 months; monthly is the averaged rate so annual == monthly * 12.
            annual_investment = sum(self._scheduled_monthly_contributions(inv.id, 12))
            rows.append({
                "name": inv.name,
                "value": inv.market_value,
                "rate": rate,
                "annual": projection.annual_income(inv.market_value, rate),
                "monthly": projection.monthly_income(inv.market_value, rate),
                "monthly_investment": annual_investment / 12.0,
                "annual_investment": annual_investment,
                "currency": inv.currency,
            })
        rows.sort(key=lambda r: r["annual"], reverse=True)
        return rows

    def get_portfolio_projected_income(self) -> dict:
        rows = self.get_income_projections()
        return {
            "annual": sum(r["annual"] for r in rows),
            "monthly": sum(r["monthly"] for r in rows),
        }

    def get_upcoming_maturities(self) -> List[dict]:
        """Holdings with a maturity date, ordered by soonest. days_remaining is
        negative for already-matured titles."""
        today = date.today()
        rows = []
        for inv in self._investments.list_investments():
            if not inv.maturity_date:
                continue
            try:
                mat = date.fromisoformat(inv.maturity_date[:10])
            except ValueError:
                continue
            rows.append({
                "name": inv.name,
                "maturity_date": inv.maturity_date,
                "days_remaining": (mat - today).days,
                "value": inv.market_value,
                "currency": inv.currency,
            })
        rows.sort(key=lambda r: r["days_remaining"])
        return rows

    def get_value_at_maturity(self) -> List[dict]:
        """For holdings with both a maturity date and a resolvable yield: the
        projected value on the maturity date (compounded from today)."""
        today = date.today()
        rows = []
        for inv in self._investments.list_investments():
            rate = self._effective_rate(inv)
            if not inv.maturity_date or rate is None:
                continue
            try:
                mat = date.fromisoformat(inv.maturity_date[:10])
            except ValueError:
                continue
            months = max((mat - today).days / 30.44, 0.0)
            projected = projection.project_value(inv.market_value, rate, months)
            rows.append({
                "name": inv.name,
                "maturity_date": inv.maturity_date,
                "current": inv.market_value,
                "projected": projected,
                "gain": projected - inv.market_value,
                "currency": inv.currency,
            })
        rows.sort(key=lambda r: r["maturity_date"])
        return rows

    def _scheduled_monthly_contributions(self, investment_id: str, months: int) -> List[float]:
        """Total scheduled contribution landing in each future month (index 1..months)."""
        buckets = [0.0] * months
        if months <= 0:
            return buckets
        today = date.today()
        horizon = _add_months(today, months)
        for sched in self._investments.list_schedules(investment_id):
            if not sched.is_active:
                continue
            start = date.fromisoformat(sched.start_date)
            end = date.fromisoformat(sched.end_date) if sched.end_date else None
            for o in sched_service.occurrences_between(
                sched.frequency, sched.interval, start, today + timedelta(days=1), horizon, end
            ):
                step = (o.year - today.year) * 12 + (o.month - today.month)
                step = max(step, 1)
                if 1 <= step <= months:
                    buckets[step - 1] += sched.amount
        return buckets

    def _asset_projection_series(self, inv, months: int) -> List[float]:
        """Projected value for one holding: yield compounding + scheduled deposits."""
        rate = self._effective_rate(inv) or 0.0
        contribs = self._scheduled_monthly_contributions(inv.id, months)
        return projection.project_value_with_contributions(inv.market_value, rate, contribs)

    def get_projected_value_by_asset(
        self, months: int = 12, asset_ids: Optional[List[str]] = None
    ) -> Tuple[List[str], Dict[str, List[float]]]:
        """One projected-value line per holding, forward `months` — yield compounded
        plus any scheduled contributions. When asset_ids is given, only those
        holdings are included (else all)."""
        holdings = self._investments.list_investments()
        if asset_ids:
            wanted = set(asset_ids)
            holdings = [h for h in holdings if h.id in wanted]
        if not holdings:
            return [], {}
        today = date.today()
        labels = [_add_months(today, m).isoformat() for m in range(months + 1)]
        series = {inv.name: self._asset_projection_series(inv, months) for inv in holdings}
        return labels, series

    def get_projected_value_series(self, months: int = 12) -> Tuple[List[str], Dict[str, List[float]]]:
        """Portfolio total projected forward `months` at each holding's yield
        (compounded). Holdings without a yield stay flat at current value."""
        holdings = self._investments.list_investments()
        if not holdings:
            return [], {}
        today = date.today()
        labels = [_add_months(today, m).isoformat() for m in range(months + 1)]
        totals = [0.0] * (months + 1)
        for inv in holdings:
            for i, v in enumerate(self._asset_projection_series(inv, months)):
                totals[i] += v
        return labels, {"projected_value": totals}

    def get_effective_rate_pct(self, asset_id: str) -> Optional[float]:
        """A holding's resolved effective annual yield, as a percentage (e.g.
        12.5), or None when it has no resolvable yield. Lets the UI prefill the
        rate when simulating extra deposits into an existing holding."""
        for inv in self._investments.list_investments():
            if inv.id == asset_id:
                rate = self._effective_rate(inv)
                return None if rate is None else rate * 100.0
        return None

    def simulate_projection(self, months: int, sims: List[dict]) -> List[float]:
        """Summed projected value (length months+1) of hypothetical investments.

        Each sim is a dict:
          {initial, monthly, contrib_months, asset_id}  -> reuse that holding's
              effective yield, or
          {initial, monthly, contrib_months, rate_pct}  -> a brand-new investment
              at the given annual %.
        `initial` is deposited now; `monthly` lands each month for the first
        `contrib_months` months (capped at the horizon); everything compounds."""
        totals = [0.0] * (months + 1)
        holdings = {inv.id: inv for inv in self._investments.list_investments()}
        for sim in sims:
            asset_id = sim.get("asset_id")
            if asset_id and asset_id in holdings:
                rate = self._effective_rate(holdings[asset_id]) or 0.0
            else:
                rate = (sim.get("rate_pct") or 0.0) / 100.0
            contrib_n = max(0, min(int(sim.get("contrib_months", months)), months))
            monthly = sim.get("monthly", 0.0) or 0.0
            contribs = [monthly] * contrib_n + [0.0] * (months - contrib_n)
            series = projection.project_value_with_contributions(
                sim.get("initial", 0.0) or 0.0, rate, contribs
            )
            for i, v in enumerate(series):
                totals[i] += v
        return totals

    def get_projected_total_invested(self, months: int = 12) -> float:
        """Net invested now plus every scheduled contribution landing within the
        next `months` months (across all holdings) — the projection's cost basis,
        against which projected value is compared to get projected gain."""
        invested = self.get_portfolio_stat(PortfolioMetric.TOTAL_INVESTED)
        for inv in self._investments.list_investments():
            invested += sum(self._scheduled_monthly_contributions(inv.id, months))
        return invested

    # -- indicators -----------------------------------------------------------

    def get_indicator_info(self, key: str) -> Optional[IndicatorInfo]:
        return INDICATORS.get(key)

    def get_indicator_series(self, key: str) -> Tuple[List[str], List[float]]:
        """(dates, values) for an economic indicator. Empty if uncached."""
        series = self._indicators.get_series(key)
        return [v.date for v in series], [v.value for v in series]

    def get_indicator_latest(self, key: str) -> Optional[float]:
        latest = self._indicators.get_latest(key)
        return latest.value if latest is not None else None
