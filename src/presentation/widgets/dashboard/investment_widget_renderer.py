from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QHeaderView, QLabel, QProgressBar, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QWidget,
)

from src.presentation import theme
from src.presentation.i18n import format_currency, format_date, format_number, t
from src.presentation.labels import asset_type_label
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation.widgets.dashboard.chart_widget import ChartWidget, PieChartWidget
from src.domain.services.investment_chart_types import (
    AllocationDimension, HoldingMetric, InvestmentSource, PortfolioMetric,
    PORTFOLIO_VALUE_METRICS, PERCENT_METRICS,
)


def holding_metric_label(metric: HoldingMetric) -> str:
    return t(f"investment.holding_metric.{metric.value}")


def portfolio_metric_label(metric: PortfolioMetric) -> str:
    return t(f"investment.portfolio_metric.{metric.value}")


def allocation_dimension_label(dimension: AllocationDimension) -> str:
    return t(f"investment.allocation_dimension.{dimension.value}")


def yield_index_label(index: str) -> str:
    return t(f"investment.yield_index.{index or 'prefixed'}")


# Additive "benchmark + spread" indices -> the benchmark name shown before the "+".
_PLUS_BENCHMARK = {"ipca_plus": "IPCA", "selic_plus": "SELIC", "cdi_plus": "CDI"}


def format_yield(rate, index: str) -> str:
    """Human-readable yield, e.g. '12% a.a.', '100% CDI', 'SELIC + 0.07%'."""
    if rate is None:
        return "—"
    idx = index or "prefixed"
    rate_str = format_number(rate, 2)
    if idx == "prefixed":
        return t("investment.yield.prefixed_fmt", rate=rate_str)
    if idx in _PLUS_BENCHMARK:
        return t("investment.yield.plus_fmt", index=_PLUS_BENCHMARK[idx], rate=rate_str)
    return t("investment.yield.of_index_fmt", rate=rate_str, index=yield_index_label(idx))


def _allocation_key_label(dimension: AllocationDimension, raw_key: str) -> str:
    if dimension == AllocationDimension.ASSET_TYPE:
        return asset_type_label(raw_key)
    return raw_key  # currency code renders as-is


def _format_value(value: float, is_percent: bool, decimals: int = 2, currency: str = "BRL") -> str:
    if is_percent:
        return f"{format_number(value, decimals)}%"
    return format_currency(value, currency)


def build_investment_content(title: str, config: dict, service) -> QWidget:
    """Render an investment dashboard widget from its config dict, mirroring the
    finance generic_widget_renderer but backed by InvestmentChartDataService."""
    source = InvestmentSource(config.get("source", InvestmentSource.PORTFOLIO_STAT.value))

    if source == InvestmentSource.PORTFOLIO_STAT:
        return _build_portfolio_stat(title, config, service)
    if source == InvestmentSource.INDICATOR_STAT:
        return _build_indicator_stat(title, config, service)
    if source == InvestmentSource.ALLOCATION:
        return _build_allocation(title, config, service)
    if source == InvestmentSource.HOLDINGS_BREAKDOWN:
        return _build_holdings_breakdown(title, config, service)
    if source == InvestmentSource.PORTFOLIO_VALUE:
        return _build_portfolio_value(title, config, service)
    if source == InvestmentSource.INDICATOR_HISTORY:
        return _build_indicator_history(title, config, service)
    if source == InvestmentSource.HOLDINGS_TABLE:
        return _build_holdings_table(title, config, service)
    if source == InvestmentSource.SAVINGS_GOALS:
        return _build_savings_goals(title, config, service)
    if source == InvestmentSource.PROJECTED_INCOME:
        return _build_projected_income(title, config, service)
    if source == InvestmentSource.PROJECTED_VALUE:
        return _build_projected_value(title, config, service)
    if source == InvestmentSource.UPCOMING_MATURITIES:
        return _build_upcoming_maturities(title, config, service)
    if source == InvestmentSource.VALUE_AT_MATURITY:
        return _build_value_at_maturity(title, config, service)
    return QLabel(t("chart.no_data"))


def _build_portfolio_stat(title, config, service) -> QWidget:
    metric = PortfolioMetric(config.get("metric", PortfolioMetric.TOTAL_MARKET_VALUE.value))
    value = service.get_portfolio_stat(metric)
    is_percent = metric in PERCENT_METRICS
    label = QLabel(_format_value(value, is_percent))
    if metric in (PortfolioMetric.TOTAL_GAIN, PortfolioMetric.RETURN_PCT):
        _color_label_by_sign(label, value)
    return make_stat_card(title, label)


def _build_indicator_stat(title, config, service) -> QWidget:
    key = config.get("indicator_key")
    info = service.get_indicator_info(key)
    value = service.get_indicator_latest(key)
    if info is None or value is None:
        return make_stat_card(title, QLabel(t("market.no_data")))
    is_percent = info.unit == "percent"
    label = QLabel(_format_value(value, is_percent, info.decimals, info.currency_code))
    return make_stat_card(title, label)


def _build_allocation(title, config, service) -> QWidget:
    dimension = AllocationDimension(config.get("dimension", AllocationDimension.ASSET_TYPE.value))
    metric = HoldingMetric(config.get("metric", HoldingMetric.MARKET_VALUE.value))
    raw_labels, values = service.get_allocation(dimension, metric)
    labels = [_allocation_key_label(dimension, k) for k in raw_labels]
    series = {holding_metric_label(metric): values}
    return _chart(config.get("chart_type", "pie"), labels, series, metric)


def _build_holdings_breakdown(title, config, service) -> QWidget:
    metric = HoldingMetric(config.get("metric", HoldingMetric.MARKET_VALUE.value))
    top_n = config.get("top_n")
    labels, values = service.get_holdings_breakdown(metric, top_n)
    series = {holding_metric_label(metric): values}
    return _chart(config.get("chart_type", "bar"), labels, series, metric)


def _build_portfolio_value(title, config, service) -> QWidget:
    dates, series_by_metric = service.get_portfolio_value_series()
    if not dates:
        chart = ChartWidget("line")
        chart.set_empty_state(t("investment.no_history"))
        return chart
    labels = [format_date(d) for d in dates]
    series = {
        portfolio_metric_label(metric): series_by_metric[metric.value]
        for metric in PORTFOLIO_VALUE_METRICS
        if metric.value in series_by_metric
    }
    chart = ChartWidget("line")
    chart.set_value_format("currency", 0, "BRL")
    chart.set_series(labels, series)
    return chart


def _build_indicator_history(title, config, service) -> QWidget:
    key = config.get("indicator_key")
    info = service.get_indicator_info(key)
    dates, values = service.get_indicator_series(key)
    chart = ChartWidget("line")
    if info is not None:
        chart.set_value_format(info.unit, info.decimals, info.currency_code)
    if not dates:
        chart.set_empty_state(t("market.no_data"))
        return chart
    labels = [format_date(d) for d in dates]
    name = t(info.label_key) if info is not None else (key or title)
    chart.set_series(labels, {name: values})
    return chart


def _build_holdings_table(title, config, service) -> QWidget:
    holdings = service.get_holdings()
    table = QTableWidget(len(holdings), 4)
    table.setHorizontalHeaderLabels([
        t("common.name"),
        t("mainwindow.table.investments.header.type"),
        t("mainwindow.table.investments.header.market_value"),
        t("mainwindow.table.investments.header.gain"),
    ])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    for i, inv in enumerate(holdings):
        table.setItem(i, 0, QTableWidgetItem(inv.name))
        table.setItem(i, 1, QTableWidgetItem(asset_type_label(inv.asset_type)))
        table.setItem(i, 2, QTableWidgetItem(format_currency(inv.market_value, inv.currency)))
        gain_item = QTableWidgetItem(
            f"{format_currency(inv.total_return, inv.currency)} ({format_number(inv.return_pct, 1)}%)"
        )
        _color_by_sign(gain_item, inv.total_return)
        table.setItem(i, 3, gain_item)
    table.resizeColumnsToContents()
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return table


def _build_savings_goals(title, config, service) -> QWidget:
    rows = service.get_savings_goals()
    if not rows:
        label = QLabel(t("investment.savings_goals.empty"))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        return label

    container = QWidget()
    outer = QVBoxLayout(container)
    outer.setContentsMargins(6, 6, 6, 6)
    outer.setSpacing(10)
    for r in rows:
        row_widget = QWidget()
        v = QVBoxLayout(row_widget)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        header = QHBoxLayout()
        header.addWidget(QLabel(r["name"]))
        header.addStretch()
        pct_label = QLabel(f"{format_number(r['pct'], 0)}%")
        header.addWidget(pct_label)
        v.addLayout(header)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(min(max(r["pct"], 0), 100)))
        bar.setTextVisible(False)
        bar.setFixedHeight(10)
        v.addWidget(bar)

        sub = "{} / {}".format(
            format_currency(r["current"], r["currency"]),
            format_currency(r["goal"], r["currency"]),
        )
        if r.get("goal_date"):
            sub += "  ·  {}".format(format_date(r["goal_date"]))
        sub_label = QLabel(sub)
        sub_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        v.addWidget(sub_label)

        # Projected ETA from yield + planned monthly contribution.
        if r["pct"] < 100:
            if r.get("eta_date"):
                eta_text = t("investment.eta_reach", when=format_date(r["eta_date"]))
            elif r.get("eta_months") is None:
                eta_text = t("investment.eta_unreachable")
            else:
                eta_text = None
            if eta_text:
                eta_label = QLabel(eta_text)
                eta_label.setStyleSheet(f"color: {theme.PRIMARY};")
                v.addWidget(eta_label)

        outer.addWidget(row_widget)
    outer.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(container)
    scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
    return scroll


def _build_projected_income(title, config, service) -> QWidget:
    chart_type = config.get("chart_type", "stat")
    if chart_type == "stat":
        totals = service.get_portfolio_projected_income()
        period = config.get("period", "annual")
        value = totals["annual"] if period == "annual" else totals["monthly"]
        return make_stat_card(title, QLabel(format_currency(value, "BRL")))

    rows = service.get_income_projections()
    chart = ChartWidget("bar")
    chart.set_value_format("currency", 0, "BRL")
    if not rows:
        chart.set_empty_state(t("investment.no_yield"))
        return chart
    labels = [r["name"] for r in rows]
    values = [r["annual"] for r in rows]
    chart.set_series(labels, {t("investment.projected_income.annual"): values})
    return chart


def _maturity_remaining_text(days: int) -> str:
    if days < 0:
        return t("investment.maturities.matured")
    if days == 0:
        return t("investment.maturities.today")
    return t("investment.maturities.in_days", days=days)


def _build_upcoming_maturities(title, config, service) -> QWidget:
    rows = service.get_upcoming_maturities()
    table = QTableWidget(len(rows), 4)
    table.setHorizontalHeaderLabels([
        t("common.name"),
        t("mainwindow.table.investments.header.maturity"),
        t("investment.maturities.remaining"),
        t("mainwindow.table.investments.header.market_value"),
    ])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    for i, r in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(r["name"]))
        table.setItem(i, 1, QTableWidgetItem(format_date(r["maturity_date"])))
        rem = QTableWidgetItem(_maturity_remaining_text(r["days_remaining"]))
        if r["days_remaining"] < 0:
            rem.setForeground(QColor(theme.EXPENSE))
        table.setItem(i, 2, rem)
        table.setItem(i, 3, QTableWidgetItem(format_currency(r["value"], r["currency"])))
    table.resizeColumnsToContents()
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return table


def _build_value_at_maturity(title, config, service) -> QWidget:
    rows = service.get_value_at_maturity()
    table = QTableWidget(len(rows), 5)
    table.setHorizontalHeaderLabels([
        t("common.name"),
        t("mainwindow.table.investments.header.maturity"),
        t("investment.value_at_maturity.current"),
        t("investment.value_at_maturity.projected"),
        t("mainwindow.table.investments.header.gain"),
    ])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    for i, r in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(r["name"]))
        table.setItem(i, 1, QTableWidgetItem(format_date(r["maturity_date"])))
        table.setItem(i, 2, QTableWidgetItem(format_currency(r["current"], r["currency"])))
        table.setItem(i, 3, QTableWidgetItem(format_currency(r["projected"], r["currency"])))
        gain = QTableWidgetItem(format_currency(r["gain"], r["currency"]))
        _color_by_sign(gain, r["gain"])
        table.setItem(i, 4, gain)
    table.resizeColumnsToContents()
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return table


def _build_projected_value(title, config, service) -> QWidget:
    months = int(config.get("months", 12))
    labels_iso, series = service.get_projected_value_series(months)
    chart = ChartWidget("line")
    chart.set_value_format("currency", 0, "BRL")
    if not labels_iso:
        chart.set_empty_state(t("chart.no_data"))
        return chart
    labels = [format_date(d) for d in labels_iso]
    chart.set_series(labels, {t("investment.projected_value.label"): series["projected_value"]})
    return chart


def _chart(chart_type: str, labels, series, metric) -> QWidget:
    is_percent = metric in PERCENT_METRICS
    if chart_type == "pie":
        widget = PieChartWidget()
        widget.set_series(labels, series)
        return widget
    widget = ChartWidget(chart_type if chart_type in ("line", "bar") else "bar")
    widget.set_value_format("percent" if is_percent else "currency", 2 if is_percent else 0, "BRL")
    widget.set_series(labels, series)
    return widget


def _color_by_sign(item, value: float) -> None:
    """Color a QTableWidgetItem by the sign of its value."""
    if value > 0:
        item.setForeground(QColor(theme.INCOME))
    elif value < 0:
        item.setForeground(QColor(theme.EXPENSE))


def _color_label_by_sign(label, value: float) -> None:
    """Color a QLabel (stat card value) by the sign of its value."""
    if value > 0:
        label.setStyleSheet(f"color: {theme.INCOME};")
    elif value < 0:
        label.setStyleSheet(f"color: {theme.EXPENSE};")
