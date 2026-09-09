from typing import Dict, List

from PySide6.QtWidgets import QAbstractItemView, QLabel, QTableWidget, QTableWidgetItem, QWidget

from src.domain.services.chart_data_service import (
    ChartDataService, ChartFilters, ChartType, DateRangeSpec, GroupByDimension, MetricType,
)
from src.presentation import theme
from src.presentation.widgets.dashboard.chart_widget import ChartWidget, PieChartWidget
from src.presentation.widgets.stat_card import make_stat_card

METRIC_LABELS = {
    MetricType.INCOME: "Income",
    MetricType.EXPENSES: "Expenses",
    MetricType.NET: "Net",
    MetricType.BALANCE: "Balance",
    MetricType.CREDIT_CARD_DEBT: "Credit Card Debt",
    MetricType.INSTALLMENT_DUE: "Installments Due",
}


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
    labels, series = _fetch_series(metrics, group_by, date_range, filters, chart_data_service)

    if chart_type == ChartType.PIE:
        widget = PieChartWidget()
    else:
        widget = ChartWidget(chart_type.value)
    widget.set_series(labels, series)
    return widget


def _fetch_series(metrics, group_by, date_range, filters, chart_data_service):
    if group_by == GroupByDimension.MONTH:
        result = chart_data_service.get_time_series(metrics, date_range, filters)
        return result.labels, result.series

    result = chart_data_service.get_breakdown(metrics, group_by, date_range, filters)
    labels = [row.dimension_label for row in result.rows]
    series = {
        metric.value: [row.values.get(metric.value, 0.0) for row in result.rows]
        for metric in metrics
    }
    return labels, series


def _format_value(value: float) -> str:
    return f"R$ {value:.2f}"


def _colorize_stat(label: QLabel, metric: MetricType, value: float) -> None:
    if metric == MetricType.EXPENSES or metric == MetricType.CREDIT_CARD_DEBT or metric == MetricType.INSTALLMENT_DUE:
        label.setStyleSheet(f"color: {theme.EXPENSE};")
    elif metric in (MetricType.NET, MetricType.BALANCE):
        label.setStyleSheet(f"color: {theme.INCOME if value >= 0 else theme.EXPENSE};")
    else:
        label.setStyleSheet(f"color: {theme.INCOME};")


def _build_table_content(title: str, config: dict, chart_data_service: ChartDataService) -> QWidget:
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
    labels, series = _fetch_series(metrics, group_by, date_range, filters, chart_data_service)
    return _build_series_table(labels, series, dimension_column="Month" if group_by == GroupByDimension.MONTH else "Category")


def _build_upcoming_installments_table(rows) -> QTableWidget:
    table = _new_table(["Due Date", "Description", "Amount"])
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(row.due_date.isoformat()))
        table.setItem(i, 1, QTableWidgetItem(f"{row.description} ({row.installment_number}/{row.installment_count})"))
        table.setItem(i, 2, QTableWidgetItem(f"R$ {row.amount:.2f}"))
    table.resizeColumnsToContents()
    return table


def _build_upcoming_recurring_table(rows) -> QTableWidget:
    table = _new_table(["Date", "Description", "Amount", "Frequency"])
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(row.occurrence_date.isoformat()))
        table.setItem(i, 1, QTableWidgetItem(row.description))
        table.setItem(i, 2, QTableWidgetItem(f"R$ {row.amount:.2f}"))
        table.setItem(i, 3, QTableWidgetItem(row.frequency_label))
    table.resizeColumnsToContents()
    return table


def _build_series_table(labels: List[str], series: Dict[str, List[float]], dimension_column: str) -> QTableWidget:
    metric_names = list(series.keys())
    table = _new_table([dimension_column] + [METRIC_LABELS.get(MetricType(m), m) for m in metric_names])
    table.setRowCount(len(labels))
    for i, label in enumerate(labels):
        table.setItem(i, 0, QTableWidgetItem(label))
        for j, metric_name in enumerate(metric_names):
            value = series[metric_name][i] if i < len(series[metric_name]) else 0.0
            table.setItem(i, j + 1, QTableWidgetItem(f"R$ {value:.2f}"))
    table.resizeColumnsToContents()
    return table


def _new_table(headers: List[str]) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    return table
