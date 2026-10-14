from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit,
    QMessageBox, QVBoxLayout, QWidget,
)

from src.presentation.i18n import t
from src.presentation.widgets.dashboard.investment_widget_renderer import (
    build_investment_content, holding_metric_label, portfolio_metric_label,
    allocation_dimension_label,
)
from src.presentation.widgets.dashboard.preview_drawer import PreviewDrawer
from src.domain.services.indicator_catalog import INDICATORS
from src.domain.services.investment_chart_types import (
    AllocationDimension, HoldingMetric, InvestmentSource, PortfolioMetric,
)


# Chart types offered per source (first is the default).
_CHART_TYPES_BY_SOURCE = {
    InvestmentSource.PORTFOLIO_STAT: ["stat"],
    InvestmentSource.INDICATOR_STAT: ["stat"],
    InvestmentSource.ALLOCATION: ["pie", "bar"],
    InvestmentSource.HOLDINGS_BREAKDOWN: ["bar", "pie"],
    InvestmentSource.PORTFOLIO_VALUE: ["line"],
    InvestmentSource.INDICATOR_HISTORY: ["line"],
    InvestmentSource.HOLDINGS_TABLE: ["table"],
    InvestmentSource.SAVINGS_GOALS: ["table"],
    InvestmentSource.PROJECTED_INCOME: ["stat", "bar"],
    InvestmentSource.PROJECTED_VALUE: ["line"],
    InvestmentSource.UPCOMING_MATURITIES: ["table"],
    InvestmentSource.VALUE_AT_MATURITY: ["table"],
    InvestmentSource.PROJECTION: ["line"],
}

_CHART_TYPE_LABEL_KEYS = {
    "line": "chart.type.line", "bar": "chart.type.bar", "pie": "chart.type.pie",
    "table": "chart.type.table", "stat": "chart.type.stat",
}


class InvestmentChartBuilderDialog(QDialog):
    def __init__(self, parent=None, service=None):
        super().__init__(parent)
        self.setWindowTitle(t("investment_builder.title"))
        self.setModal(True)
        self.resize(760, 520)
        self._service = service

        outer = QVBoxLayout(self)
        content_row = QHBoxLayout()

        form_panel = QWidget()
        self._form = QFormLayout(form_panel)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText(t("investment_builder.title_placeholder"))
        self._title_edit.textChanged.connect(self._refresh_preview)
        self._form.addRow(t("chart_builder.field.title"), self._title_edit)

        self._source_combo = QComboBox()
        for source in InvestmentSource:
            self._source_combo.addItem(t(f"investment.source.{source.value}"), source.value)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        self._form.addRow(t("investment_builder.field.source"), self._source_combo)

        self._chart_type_combo = QComboBox()
        self._chart_type_combo.currentIndexChanged.connect(self._refresh_preview)
        self._form.addRow(t("chart_builder.field.chart_type"), self._chart_type_combo)

        self._metric_combo = QComboBox()
        self._metric_combo.currentIndexChanged.connect(self._refresh_preview)
        self._form.addRow(t("investment_builder.field.metric"), self._metric_combo)

        self._dimension_combo = QComboBox()
        for dim in AllocationDimension:
            self._dimension_combo.addItem(allocation_dimension_label(dim), dim.value)
        self._dimension_combo.currentIndexChanged.connect(self._refresh_preview)
        self._form.addRow(t("investment_builder.field.dimension"), self._dimension_combo)

        self._indicator_combo = QComboBox()
        for key, info in INDICATORS.items():
            self._indicator_combo.addItem(t(info.label_key), key)
        self._indicator_combo.currentIndexChanged.connect(self._refresh_preview)
        self._form.addRow(t("investment_builder.field.indicator"), self._indicator_combo)

        content_row.addWidget(form_panel, stretch=1)
        self._preview = PreviewDrawer()
        content_row.addWidget(self._preview)
        outer.addLayout(content_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._on_source_changed()

    def _current_source(self) -> InvestmentSource:
        return InvestmentSource(self._source_combo.currentData())

    def _on_source_changed(self):
        source = self._current_source()

        # Chart types for this source.
        self._chart_type_combo.blockSignals(True)
        self._chart_type_combo.clear()
        for ct in _CHART_TYPES_BY_SOURCE[source]:
            self._chart_type_combo.addItem(t(_CHART_TYPE_LABEL_KEYS[ct]), ct)
        self._chart_type_combo.blockSignals(False)

        # Metric options depend on the source.
        self._metric_combo.blockSignals(True)
        self._metric_combo.clear()
        if source == InvestmentSource.PORTFOLIO_STAT:
            for m in PortfolioMetric:
                self._metric_combo.addItem(portfolio_metric_label(m), m.value)
        elif source in (InvestmentSource.ALLOCATION, InvestmentSource.HOLDINGS_BREAKDOWN):
            for m in HoldingMetric:
                self._metric_combo.addItem(holding_metric_label(m), m.value)
        self._metric_combo.blockSignals(False)

        # Row visibility.
        self._form.setRowVisible(self._chart_type_combo, len(_CHART_TYPES_BY_SOURCE[source]) > 1)
        self._form.setRowVisible(
            self._metric_combo,
            source in (InvestmentSource.PORTFOLIO_STAT, InvestmentSource.ALLOCATION,
                       InvestmentSource.HOLDINGS_BREAKDOWN),
        )
        self._form.setRowVisible(self._dimension_combo, source == InvestmentSource.ALLOCATION)
        self._form.setRowVisible(
            self._indicator_combo,
            source in (InvestmentSource.INDICATOR_HISTORY, InvestmentSource.INDICATOR_STAT),
        )
        self._refresh_preview()

    def _build_config(self) -> dict:
        source = self._current_source()
        config = {"source": source.value, "chart_type": self._chart_type_combo.currentData()}
        if source in (InvestmentSource.PORTFOLIO_STAT, InvestmentSource.ALLOCATION,
                      InvestmentSource.HOLDINGS_BREAKDOWN):
            config["metric"] = self._metric_combo.currentData()
        if source == InvestmentSource.ALLOCATION:
            config["dimension"] = self._dimension_combo.currentData()
        if source in (InvestmentSource.INDICATOR_HISTORY, InvestmentSource.INDICATOR_STAT):
            config["indicator_key"] = self._indicator_combo.currentData()
        return config

    def _refresh_preview(self, *_args):
        title = self._title_edit.text().strip() or t("chart.preview.title")
        self._preview.set_title(title)
        if self._service is None:
            self._preview.show_placeholder(t("chart_builder.preview.unavailable"))
            return
        config = self._build_config()
        try:
            content = build_investment_content(title, config, self._service)
        except Exception:
            self._preview.show_placeholder(t("chart_builder.preview.render_error"))
            return
        self._preview.show_content(content, center=(config["chart_type"] == "stat"))

    def _validate_and_accept(self):
        if not self._title_edit.text().strip():
            QMessageBox.warning(
                self, t("chart_builder.validation.title"), t("chart_builder.validation.title_required")
            )
            return
        self.accept()

    def get_data(self) -> dict:
        return {"title": self._title_edit.text().strip(), "config": self._build_config()}
