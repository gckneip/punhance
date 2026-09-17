from datetime import date
from typing import Dict, List

from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QWidget,
)

from src.domain.services.chart_data_service import (
    ChartDataService, ChartFilters, ChartType, DateRangeSpec, GroupByDimension, MetricType,
)
from src.presentation import i18n, theme
from src.presentation.i18n import t
from src.presentation.widgets.dashboard.chart_widget import ChartWidget, PieChartWidget
from src.presentation.widgets.even_columns_table import EvenColumnsTableWidget
from src.presentation.widgets.stat_card import make_stat_card


def _metric_label(metric: MetricType) -> str:
    """Translated display label for a metric (resolved at call time so it picks
    up the active language)."""
    keys = {
        MetricType.INCOME: "renderer.metric.income",
        MetricType.EXPENSES: "renderer.metric.expenses",
        MetricType.NET: "renderer.metric.net",
        MetricType.BALANCE: "renderer.metric.balance",
        MetricType.CREDIT_CARD_DEBT: "renderer.metric.credit_card_debt",
        MetricType.INSTALLMENT_DUE: "renderer.metric.installment_due",
    }
    key = keys.get(metric)
    return t(key) if key else metric.value


# Public alias for use by other presentation modules (e.g. the chart builder).
metric_label = _metric_label


def _dimension_column_label(dimension: GroupByDimension) -> str:
    """Translated table column header for a group-by dimension."""
    keys = {
        GroupByDimension.MONTH: "renderer.dimension.month",
        GroupByDimension.CATEGORY: "common.category",
        GroupByDimension.ACCOUNT: "common.account",
        GroupByDimension.COUNTERPARTY: "renderer.dimension.counterparty",
        GroupByDimension.CREDIT_CARD: "renderer.dimension.credit_card",
        GroupByDimension.PRODUCT: "renderer.dimension.product",
    }
    key = keys.get(dimension)
    return t(key) if key else dimension.value


def widget_supports_date_range(config: dict) -> bool:
    """Whether changing config["date_range"] has any effect on this widget's
    data. Some breakdowns (credit card debt, account balances) are always a
    live snapshot and ignore date_range entirely - showing a selector for
    those would be misleading."""
    if "date_range" not in config:
        return False
    if config.get("data_source"):
        return False
    if config.get("group_by") == "credit_card":
        return False
    metrics = config.get("metrics") or []
    if metrics and all(m in ("balance", "credit_card_debt") for m in metrics):
        return False
    return True


def widget_supports_period_ahead(config: dict) -> bool:
    """Whether this widget has a "how far into the future" window that a
    PeriodAheadSelector can drive - true for the upcoming-installments/
    -recurring/-events table data sources, which all key off days_ahead."""
    return "days_ahead" in config


def build_generic_content(title: str, config: dict, chart_data_service: ChartDataService) -> QWidget:
    chart_type = ChartType(config["chart_type"])

    if chart_type == ChartType.TABLE:
        return _build_table_content(title, config, chart_data_service)

    metrics = [MetricType(m) for m in config["metrics"]]
    date_range = DateRangeSpec.from_dict(config["date_range"])
    filters = ChartFilters.from_dict(config.get("filters"))

    if chart_type == ChartType.STAT:
        value = chart_data_service.get_stat(metrics[0], date_range, filters)
        label = QLabel(_format_value(value))
        _colorize_stat(label, metrics[0], value)
        return make_stat_card(title, label)

    group_by = GroupByDimension(config["group_by"])
    # Forecasting only applies to monthly line charts (a dashed future tail);
    # bar/pie and non-month groupings ignore it.
    forecast_months = int(config.get("forecast_months") or 0) if chart_type == ChartType.LINE else 0
    labels, series, forecast_count = _fetch_series(
        metrics, group_by, date_range, filters, chart_data_service, config, forecast_months,
    )

    # Localize the legend (series) keys before handing them to the chart.
    display_series = _display_series(series, _split_by(config))
    if chart_type == ChartType.PIE:
        widget = PieChartWidget()
        widget.set_series(labels, display_series)
    else:
        widget = ChartWidget(chart_type.value)
        widget.set_series(labels, display_series, forecast_count)
    return widget


def _fetch_series(metrics, group_by, date_range, filters, chart_data_service, config=None, forecast_months=0):
    split_by = _split_by(config)
    if group_by == GroupByDimension.MONTH:
        if split_by is not None:
            result = chart_data_service.get_time_series_breakdown(
                metrics[0], split_by, date_range, filters,
                top_n=(config or {}).get("top_n"), forecast_months=forecast_months,
            )
            labels = [_format_month_label(label) for label in result.labels]
            return labels, result.series, result.forecast_count
        result = chart_data_service.get_time_series(
            metrics, date_range, filters, forecast_months=forecast_months,
        )
        labels = [_format_month_label(label) for label in result.labels]
        return labels, result.series, result.forecast_count

    result = chart_data_service.get_breakdown(metrics, group_by, date_range, filters)
    labels = [_display_label(row.dimension_label) for row in result.rows]
    series = {
        metric.value: [row.values.get(metric.value, 0.0) for row in result.rows]
        for metric in metrics
    }
    return labels, series, 0


def _split_by(config):
    value = (config or {}).get("split_by")
    return GroupByDimension(value) if value else None


# Domain services emit a few fixed English bucket labels (clean-architecture:
# the domain stays presentation-free). Map them to translation keys at display.
_DOMAIN_LABEL_KEYS = {
    "Other": "renderer.label.other",
    "Total": "renderer.label.total",
    "Uncategorized": "renderer.label.uncategorized",
    "No counterparty": "renderer.label.no_counterparty",
    "Unknown product": "renderer.label.unknown_product",
}


def _display_label(raw):
    """Translate a fixed domain bucket label; pass other values through."""
    key = _DOMAIN_LABEL_KEYS.get(raw)
    return t(key) if key else raw


def _format_month_label(raw):
    """Format a domain 'YYYY-MM' month bucket into a localized month + year."""
    try:
        year, month = str(raw).split("-")
        return i18n.format_month_year(date(int(year), int(month), 1))
    except (ValueError, IndexError, TypeError):
        return raw


def _display_series(series, split_by):
    """Localize the series (legend) keys for charts.

    When there is no split, the keys are metric machine names → metric labels.
    When split by a dimension, the keys are dimension values (which may include
    the fixed 'Other' bucket) → localized dimension labels.
    """
    if split_by is None:
        out = {}
        for key, values in series.items():
            try:
                out[_metric_label(MetricType(key))] = values
            except ValueError:
                out[key] = values
        return out
    return {_display_label(key): values for key, values in series.items()}


def _format_value(value: float) -> str:
    return i18n.format_currency(value, "BRL")


def _colorize_stat(label: QLabel, metric: MetricType, value: float) -> None:
    if metric == MetricType.EXPENSES or metric == MetricType.CREDIT_CARD_DEBT or metric == MetricType.INSTALLMENT_DUE:
        label.setStyleSheet(f"color: {theme.EXPENSE};")
    elif metric in (MetricType.NET, MetricType.BALANCE):
        label.setStyleSheet(f"color: {theme.INCOME if value >= 0 else theme.EXPENSE};")
    else:
        label.setStyleSheet(f"color: {theme.INCOME};")


def _build_table_content(title: str, config: dict, chart_data_service: ChartDataService) -> QWidget:
    if config.get("data_source") == "upcoming_events":
        filters = ChartFilters.from_dict(config.get("filters"))
        rows = chart_data_service.get_upcoming_events(
            days_ahead=config.get("days_ahead", 30), filters=filters,
        )
        return _build_upcoming_events_table(rows)

    if config.get("data_source") == "upcoming_installments":
        filters = ChartFilters.from_dict(config.get("filters"))
        rows = chart_data_service.get_upcoming_installments(
            days_ahead=config.get("days_ahead", 30), filters=filters,
        )
        return _build_upcoming_installments_table(rows)

    if config.get("data_source") == "upcoming_recurring_events":
        filters = ChartFilters.from_dict(config.get("filters"))
        rows = chart_data_service.get_upcoming_recurring_occurrences(
            days_ahead=config.get("days_ahead", 30), filters=filters,
        )
        return _build_upcoming_recurring_table(rows)

    metrics = [MetricType(m) for m in config["metrics"]]
    group_by = GroupByDimension(config["group_by"])
    date_range = DateRangeSpec.from_dict(config["date_range"])
    filters = ChartFilters.from_dict(config.get("filters"))
    split_by = _split_by(config)
    labels, series, _forecast_count = _fetch_series(
        metrics, group_by, date_range, filters, chart_data_service, config,
    )
    dimension_column = _dimension_column_label(group_by)
    table = _build_series_table(
        labels, series, dimension_column=dimension_column, series_are_metrics=split_by is None,
    )

    if group_by == GroupByDimension.PRODUCT:
        return _build_table_with_pie(table, labels, series)
    return table


def _build_table_with_pie(table: QTableWidget, labels: List[str], series: Dict[str, List[float]]) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(table, 2)

    pie = PieChartWidget()
    pie.set_series(labels, series)
    layout.addWidget(pie, 1)
    return container


def _build_upcoming_installments_table(rows) -> QTableWidget:
    table = _new_table([t("renderer.col.due_date"), t("common.description"), t("common.amount")])
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(i18n.format_date(row.due_date)))
        table.setItem(i, 1, QTableWidgetItem(f"{row.description} ({row.installment_number}/{row.installment_count})"))
        table.setItem(i, 2, QTableWidgetItem(i18n.format_currency(row.amount, getattr(row, "currency", "BRL"))))
    table.resizeColumnsToContents()
    return table


def _build_upcoming_events_table(rows) -> QTableWidget:
    table = _new_table([
        t("common.date"), t("common.type"), t("common.description"),
        t("common.amount"), t("renderer.col.details"),
    ])
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(i18n.format_date(row.event_date)))
        kind_label = t("renderer.kind.installment") if row.kind == "installment" else t("renderer.kind.recurring")
        table.setItem(i, 1, QTableWidgetItem(kind_label))
        table.setItem(i, 2, QTableWidgetItem(row.description))
        table.setItem(i, 3, QTableWidgetItem(i18n.format_currency(row.amount, getattr(row, "currency", "BRL"))))
        table.setItem(i, 4, QTableWidgetItem(row.detail))
    table.resizeColumnsToContents()
    return table


def _build_upcoming_recurring_table(rows) -> QTableWidget:
    table = _new_table([
        t("common.date"), t("common.description"), t("common.amount"), t("renderer.col.frequency"),
    ])
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(i18n.format_date(row.occurrence_date)))
        table.setItem(i, 1, QTableWidgetItem(row.description))
        table.setItem(i, 2, QTableWidgetItem(i18n.format_currency(row.amount, getattr(row, "currency", "BRL"))))
        table.setItem(i, 3, QTableWidgetItem(row.frequency_label))
    table.resizeColumnsToContents()
    return table


def _build_series_table(
    labels: List[str], series: Dict[str, List[float]], dimension_column: str, series_are_metrics: bool = True,
) -> QTableWidget:
    metric_names = list(series.keys())
    if series_are_metrics:
        headers = [_metric_label(MetricType(m)) for m in metric_names]
    else:
        headers = metric_names
    table = _new_table([dimension_column] + headers)
    table.setRowCount(len(labels))
    for i, label in enumerate(labels):
        table.setItem(i, 0, QTableWidgetItem(label))
        for j, metric_name in enumerate(metric_names):
            value = series[metric_name][i] if i < len(series[metric_name]) else 0.0
            table.setItem(i, j + 1, QTableWidgetItem(i18n.format_currency(value, "BRL")))
    table.resizeColumnsToContents()
    return table


def _new_table(headers: List[str]) -> QTableWidget:
    # EvenColumnsTableWidget (not a plain QTableWidget) so leftover viewport
    # width - e.g. when this table sits next to a pie chart with more room
    # than its content needs - gets spread across the columns instead of
    # showing up as blank space after the last column.
    table = EvenColumnsTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    return table
