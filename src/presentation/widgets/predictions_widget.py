from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QMenu, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.presentation import icons, theme
from src.presentation.i18n import CURRENCY_SYMBOLS, format_currency, format_date, format_number, t
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation.widgets.currency_spin_box import CurrencySpinBox
from src.presentation.widgets.dashboard.chart_widget import ChartWidget, PieChartWidget
from src.presentation.widgets.dashboard.investment_widget_renderer import build_investment_content
from src.domain.services.investment_chart_types import InvestmentSource, PortfolioMetric

# Projection horizons offered on-screen (months).
_MONTH_OPTIONS = [6, 12, 24, 36, 60]

_VIEW_TOTAL = "total"
_VIEW_BY_ASSET = "by_asset"


class _KeepOpenMenu(QMenu):
    """A QMenu that stays open when a checkable item is toggled, so several
    assets can be ticked without the menu closing after each click."""

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action is not None and action.isCheckable() and action.isEnabled():
            action.trigger()
            return
        super().mouseReleaseEvent(event)


class SimulationPanel(QWidget):
    """A small form to layer hypothetical future investments onto the projection
    chart: pick a new investment (with its own yield) or an existing holding
    (reusing its yield), set an initial amount, a monthly contribution and a
    contribution period, and stack them up. Emits ``changed`` whenever the list
    of simulations changes."""

    changed = Signal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._sims = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel(t("predictions.sim.title"))
        title.setObjectName("sectionHeader")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)
        # Let the input column take all the slack so values/arrows aren't clipped.
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        field_min_width = 120

        self._target = QComboBox()
        self._target.setMinimumWidth(field_min_width)
        self._target.currentIndexChanged.connect(self._on_target_changed)
        form.addRow(t("predictions.sim.target"), self._target)

        self._rate = QDoubleSpinBox()
        self._rate.setRange(0, 10000)
        self._rate.setDecimals(2)
        self._rate.setSuffix(" %")
        self._rate.setMinimumWidth(field_min_width)
        form.addRow(t("predictions.sim.rate"), self._rate)

        prefix = CURRENCY_SYMBOLS["BRL"] + " "
        self._initial = CurrencySpinBox()
        self._initial.setRange(0, 999999999)
        self._initial.setPrefix(prefix)
        self._initial.setMinimumWidth(field_min_width)
        form.addRow(t("predictions.sim.initial"), self._initial)

        self._monthly = CurrencySpinBox()
        self._monthly.setRange(0, 999999999)
        self._monthly.setPrefix(prefix)
        self._monthly.setMinimumWidth(field_min_width)
        form.addRow(t("predictions.sim.monthly"), self._monthly)

        self._period = QSpinBox()
        self._period.setRange(1, 600)
        self._period.setValue(12)
        self._period.setSuffix(" " + t("predictions.sim.months_suffix"))
        self._period.setMinimumWidth(field_min_width)
        form.addRow(t("predictions.sim.period"), self._period)

        layout.addLayout(form)

        add_btn = QPushButton(t("predictions.sim.add"))
        add_btn.setIcon(icons.icon("fa6s.plus"))
        add_btn.clicked.connect(self._on_add)
        layout.addWidget(add_btn)

        # Active simulations, each with a remove button.
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self._list_container)
        # Let this list collapse freely: its default minimum height would
        # otherwise steal space from the form above and squash the input fields
        # below the height their text needs (clipping the values vertically).
        scroll.setMinimumHeight(0)
        scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.addWidget(scroll, 1)

        self._clear_btn = QPushButton(t("predictions.sim.clear"))
        self._clear_btn.setIcon(icons.icon("fa6s.trash"))
        self._clear_btn.clicked.connect(self._on_clear)
        layout.addWidget(self._clear_btn)

        self.refresh_targets()

    # -- public ---------------------------------------------------------------

    def simulations(self):
        return list(self._sims)

    def refresh_targets(self):
        prev = self._target.currentData()
        self._target.blockSignals(True)
        self._target.clear()
        self._target.addItem(t("predictions.sim.new_investment"), None)
        for inv in self._service.get_holdings():
            self._target.addItem(inv.name, inv.id)
        idx = self._target.findData(prev)
        if idx >= 0:
            self._target.setCurrentIndex(idx)
        self._target.blockSignals(False)
        self._on_target_changed()

    # -- internals ------------------------------------------------------------

    def _on_target_changed(self):
        asset_id = self._target.currentData()
        if asset_id is None:
            self._rate.setEnabled(True)
        else:
            # Existing holding: reuse its resolved yield, shown read-only.
            self._rate.setEnabled(False)
            rate = self._service.get_effective_rate_pct(asset_id)
            self._rate.setValue(rate or 0.0)

    def _on_add(self):
        asset_id = self._target.currentData()
        initial = self._initial.value()
        monthly = self._monthly.value()
        if not initial and not monthly:
            return
        contrib_months = self._period.value()
        sim = {
            "asset_id": asset_id,
            "rate_pct": None if asset_id is not None else self._rate.value(),
            "initial": initial,
            "monthly": monthly,
            "contrib_months": contrib_months,
        }
        sim["label"] = self._label_for(sim)
        self._sims.append(sim)
        self._append_list_row(sim)
        self._initial.setValue(0)
        self._monthly.setValue(0)
        self.changed.emit()

    def _label_for(self, sim) -> str:
        asset_id = sim["asset_id"]
        if asset_id is not None:
            name = self._target.itemText(self._target.findData(asset_id))
        else:
            name = t("predictions.sim.new_short", rate=format_number(sim["rate_pct"], 2))
        parts = []
        if sim["initial"]:
            parts.append(format_currency(sim["initial"], "BRL"))
        if sim["monthly"]:
            parts.append(t("predictions.sim.monthly_short",
                           amount=format_currency(sim["monthly"], "BRL"),
                           months=sim["contrib_months"]))
        return f"{name} · " + " + ".join(parts) if parts else name

    def _append_list_row(self, sim):
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        label = QLabel(sim["label"])
        label.setWordWrap(True)
        row.addWidget(label, 1)
        remove = QPushButton()
        remove.setIcon(icons.icon("fa6s.xmark", color=theme.EXPENSE))
        remove.setFixedSize(24, 24)
        remove.setToolTip(t("common.delete"))
        remove.clicked.connect(lambda: self._on_remove(sim, row_widget))
        row.addWidget(remove)
        self._list_layout.addWidget(row_widget)

    def _on_remove(self, sim, row_widget):
        if sim in self._sims:
            self._sims.remove(sim)
        row_widget.setParent(None)
        row_widget.deleteLater()
        self.changed.emit()

    def _on_clear(self):
        if not self._sims:
            return
        self._sims.clear()
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.changed.emit()


class PredictionsWidget(QWidget):
    """A full "Predictions" screen for Investments mode: a wider, richer take on
    the projection widget.

    Combines, driven by a shared period/asset/view control bar:
      - summary stat cards (projected monthly/annual income, projected portfolio
        value at the horizon, and projected gain),
      - an interactive value-projection chart (portfolio total or per asset),
      - a projected-income table (per holding),
      - and reused maturities / value-at-maturity / savings-goals sections.
    """

    def __init__(self, investment_chart_data_service, parent=None):
        super().__init__(parent)
        self._service = investment_chart_data_service
        self._months = 12
        self._view = _VIEW_TOTAL
        self._selected_ids = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        self._content = QVBoxLayout(content)
        self._content.setContentsMargins(4, 4, 4, 4)
        self._content.setSpacing(10)
        scroll.setWidget(content)

        self._build_controls()

        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(8)
        self._content.addLayout(self._cards_row)

        self._content.addWidget(self._section_label(t("investment.source.projected_value")))
        self._chart = ChartWidget("line")
        self._chart.set_value_format("currency", 0, "BRL")
        # Fixed height: inside a scroll area, an expanding chart gets compressed
        # to a sliver when it competes with the tables below it. Tall enough to
        # fit the simulation form beside it without squashing its input fields.
        self._fix_height(self._chart, 380)

        # The chart and the "what-if" simulation panel sit side by side.
        self._sim_panel = SimulationPanel(self._service)
        self._sim_panel.changed.connect(self._render_chart)
        self._fix_height(self._sim_panel, 380)

        chart_row = QWidget()
        chart_hbox = QHBoxLayout(chart_row)
        chart_hbox.setContentsMargins(0, 0, 0, 0)
        chart_hbox.setSpacing(8)
        chart_hbox.addWidget(self._chart, 2)
        chart_hbox.addWidget(self._sim_panel, 1)
        self._content.addWidget(chart_row)

        self._content.addWidget(self._section_label(t("investment.source.projected_income")))
        self._income_holder = self._section_holder()

        self._content.addWidget(self._section_label(t("investment.source.upcoming_maturities")))
        self._maturities_holder = self._section_holder()

        self._content.addWidget(self._section_label(t("investment.source.value_at_maturity")))
        self._value_at_maturity_holder = self._section_holder()

        self._content.addWidget(self._section_label(t("investment.source.savings_goals")))
        self._goals_holder = self._section_holder()

        self._content.addStretch()

        self._rebuild_assets_menu()
        self.refresh()

    # -- scaffolding ----------------------------------------------------------

    def _section_label(self, text) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionHeader")
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    def _section_holder(self) -> QVBoxLayout:
        container = QWidget()
        holder = QVBoxLayout(container)
        holder.setContentsMargins(0, 0, 0, 0)
        self._content.addWidget(container)
        return holder

    @staticmethod
    def _fill(holder: QVBoxLayout, widget: QWidget):
        while holder.count():
            item = holder.takeAt(0)
            old = item.widget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
        holder.addWidget(widget)

    @staticmethod
    def _fix_height(widget: QWidget, height: int):
        """Pin a widget's height and stop the vertical layout from stretching or
        compressing it — the only reliable way to stack charts and tables in a
        scroll area without them fighting over space."""
        widget.setMinimumHeight(height)
        widget.setMaximumHeight(height)
        policy = widget.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Fixed)
        widget.setSizePolicy(policy)

    def _cap_table_height(self, widget: QWidget):
        """Size a table to its rows (header + rows), capped so long tables scroll
        internally instead of pushing the page arbitrarily tall."""
        rows = widget.rowCount() if isinstance(widget, QTableWidget) else 0
        height = 36 + max(rows, 1) * 34
        self._fix_height(widget, min(height, 320))

    # -- controls -------------------------------------------------------------

    def _build_controls(self):
        controls = QHBoxLayout()

        controls.addWidget(QLabel(t("investment.projection.period")))
        self._period_combo = QComboBox()
        for n in sorted(set(_MONTH_OPTIONS) | {self._months}):
            self._period_combo.addItem(t("investment.projection.n_months", n=n), n)
        idx = self._period_combo.findData(self._months)
        if idx >= 0:
            self._period_combo.setCurrentIndex(idx)
        self._period_combo.currentIndexChanged.connect(self._on_period_changed)
        controls.addWidget(self._period_combo)

        controls.addSpacing(12)
        controls.addWidget(QLabel(t("predictions.view")))
        self._view_combo = QComboBox()
        self._view_combo.addItem(t("predictions.view.total"), _VIEW_TOTAL)
        self._view_combo.addItem(t("predictions.view.by_asset"), _VIEW_BY_ASSET)
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        controls.addWidget(self._view_combo)

        controls.addSpacing(12)
        controls.addWidget(QLabel(t("investment.projection.assets")))
        self._assets_button = QPushButton()
        self._assets_menu = _KeepOpenMenu(self._assets_button)
        self._assets_button.setMenu(self._assets_menu)
        controls.addWidget(self._assets_button)

        controls.addStretch()
        self._content.addLayout(controls)

    def _rebuild_assets_menu(self):
        self._assets_menu.clear()
        holdings = self._service.get_holdings()
        valid_ids = {h.id for h in holdings}
        self._selected_ids &= valid_ids
        for inv in holdings:
            action = self._assets_menu.addAction(inv.name)
            action.setCheckable(True)
            action.setChecked(inv.id in self._selected_ids)
            action.toggled.connect(lambda checked, iid=inv.id: self._on_asset_toggled(iid, checked))
        self._update_assets_button_text()
        self._assets_button.setEnabled(self._view == _VIEW_BY_ASSET)

    def _update_assets_button_text(self):
        if not self._selected_ids:
            self._assets_button.setText(t("investment.projection.all_assets"))
        else:
            self._assets_button.setText(t("investment.projection.n_selected", n=len(self._selected_ids)))

    def _on_period_changed(self):
        self._months = self._period_combo.currentData()
        self.refresh()

    def _on_view_changed(self):
        self._view = self._view_combo.currentData()
        self._assets_button.setEnabled(self._view == _VIEW_BY_ASSET)
        self._render_chart()

    def _on_asset_toggled(self, investment_id, checked):
        if checked:
            self._selected_ids.add(investment_id)
        else:
            self._selected_ids.discard(investment_id)
        self._update_assets_button_text()
        self._render_chart()

    # -- rendering ------------------------------------------------------------

    def refresh(self):
        self._rebuild_assets_menu()
        self._sim_panel.refresh_targets()
        self._render_cards()
        self._render_chart()
        self._render_income()
        self._fill(self._maturities_holder, self._reused_table(InvestmentSource.UPCOMING_MATURITIES))
        self._fill(self._value_at_maturity_holder, self._reused_table(InvestmentSource.VALUE_AT_MATURITY))
        goals = self._reused(InvestmentSource.SAVINGS_GOALS)
        self._fix_height(goals, 220)
        self._fill(self._goals_holder, goals)

    def _reused(self, source: InvestmentSource) -> QWidget:
        return build_investment_content("", {"source": source.value}, self._service)

    def _reused_table(self, source: InvestmentSource) -> QWidget:
        widget = self._reused(source)
        self._cap_table_height(widget)
        return widget

    def _render_cards(self):
        while self._cards_row.count():
            item = self._cards_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        _, series = self._service.get_projected_value_series(self._months)
        projected_value = series["projected_value"][-1] if series.get("projected_value") else 0.0
        invested_now = self._service.get_portfolio_stat(PortfolioMetric.TOTAL_INVESTED)
        projected_invested = self._service.get_projected_total_invested(self._months)
        projected_gain = projected_value - projected_invested

        cards = [
            (t("predictions.stat.invested_now"), format_currency(invested_now, "BRL"), None),
            (t("predictions.stat.projected_invested", n=self._months),
             format_currency(projected_invested, "BRL"), None),
            (t("predictions.stat.projected_value", n=self._months),
             format_currency(projected_value, "BRL"), None),
            (t("predictions.stat.projected_gain", n=self._months),
             format_currency(projected_gain, "BRL"), projected_gain),
        ]
        for title, value, sign in cards:
            label = QLabel(value)
            if sign is not None:
                if sign > 0:
                    label.setStyleSheet(f"color: {theme.INCOME};")
                elif sign < 0:
                    label.setStyleSheet(f"color: {theme.EXPENSE};")
            self._cards_row.addWidget(make_stat_card(title, label))

    def _render_chart(self):
        base_labels, base = self._service.get_projected_value_series(self._months)
        base_total = base.get("projected_value") if base else None
        if self._view == _VIEW_TOTAL:
            labels_iso = base_labels
            series = {t("investment.projected_value.label"): base_total} if base_total else {}
        else:
            labels_iso, series = self._service.get_projected_value_by_asset(
                self._months, sorted(self._selected_ids) or None
            )
        if not labels_iso or not series:
            self._chart.set_empty_state(t("chart.no_data"))
            return
        # Overlay the "what-if" simulation as an extra line = base portfolio
        # projection plus the simulated investments' projected value.
        sims = self._sim_panel.simulations()
        if sims and base_total:
            added = self._service.simulate_projection(self._months, sims)
            series = dict(series)
            series[t("predictions.sim.with_simulation")] = [b + a for b, a in zip(base_total, added)]
        labels = [format_date(d) for d in labels_iso]
        self._chart.set_series(labels, series)

    def _render_income(self):
        rows = self._service.get_income_projections()
        if not rows:
            label = QLabel(t("investment.no_yield"))
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
            self._fill(self._income_holder, label)
            return

        # One extra row at the bottom for the column totals.
        table = QTableWidget(len(rows) + 1, 7)
        table.setObjectName("mainTabTable")
        table.setHorizontalHeaderLabels([
            t("common.name"),
            t("investment.holding_metric.market_value"),
            t("predictions.income.rate"),
            t("predictions.income.monthly"),
            t("predictions.income.annual"),
            t("predictions.income.invest_monthly"),
            t("predictions.income.invest_annual"),
        ])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        # Keep names on a single line: a squeezed name column would otherwise
        # wrap and make rows tall.
        table.setWordWrap(False)
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(r["name"]))
            table.setItem(i, 1, QTableWidgetItem(format_currency(r["value"], r["currency"])))
            table.setItem(i, 2, QTableWidgetItem(f"{format_number(r['rate'], 2)}%"))
            monthly = QTableWidgetItem(format_currency(r["monthly"], r["currency"]))
            monthly.setForeground(QColor(theme.INCOME))
            table.setItem(i, 3, monthly)
            annual = QTableWidgetItem(format_currency(r["annual"], r["currency"]))
            annual.setForeground(QColor(theme.INCOME))
            table.setItem(i, 4, annual)
            table.setItem(i, 5, QTableWidgetItem(self._investment_cell(r["monthly_investment"], r["currency"])))
            table.setItem(i, 6, QTableWidgetItem(self._investment_cell(r["annual_investment"], r["currency"])))
        self._add_income_total_row(table, len(rows), rows)
        # ResizeToContents on the header sizes each column to the WIDER of its
        # header label and its cells (plain resizeColumnsToContents ignores the
        # header, truncating longer labels like "Valor de mercado"). The name
        # column stretches so the table fills the width it's given.
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # Size rows AFTER the columns are final so heights reflect the single-line
        # (non-wrapped) content, not the pre-stretch column widths.
        table.resizeRowsToContents()

        # A pie of annual income per asset, so the biggest income contributors
        # read at a glance below the detailed table. Stacked (not side by side)
        # so the now-wider table keeps all its columns on screen.
        pie = PieChartWidget()
        pie.set_series(
            [r["name"] for r in rows],
            {t("predictions.income.annual"): [r["annual"] for r in rows]},
        )

        # Size the table to fit every row (data + the totals footer) so the
        # total is always visible; the page's own scroll handles overflow. Cap
        # it for very large portfolios so it can't grow unbounded.
        content_h = sum(table.rowHeight(r) for r in range(table.rowCount()))
        header_h = table.horizontalHeader().sizeHint().height()
        table_h = min(content_h + header_h + 4, 640)
        pie_h = 240
        self._fix_height(table, table_h)
        self._fix_height(pie, pie_h)

        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)
        col.addWidget(table)
        col.addWidget(pie)
        self._fix_height(container, table_h + pie_h + 8)
        self._fill(self._income_holder, container)

    @staticmethod
    def _investment_cell(value: float, currency: str) -> str:
        """Scheduled-contribution amount, dashed out when there's no plan."""
        return format_currency(value, currency) if value else "—"

    def _add_income_total_row(self, table, row, rows):
        """A bold footer row summing every money column. Yield is left blank —
        summing per-asset percentages is meaningless."""
        total_value = sum(r["value"] for r in rows)
        total_monthly = sum(r["monthly"] for r in rows)
        total_annual = sum(r["annual"] for r in rows)
        total_monthly_inv = sum(r["monthly_investment"] for r in rows)
        total_annual_inv = sum(r["annual_investment"] for r in rows)

        cells = [
            (0, t("predictions.income.total"), None),
            (1, format_currency(total_value, "BRL"), None),
            (2, "", None),
            (3, format_currency(total_monthly, "BRL"), theme.INCOME),
            (4, format_currency(total_annual, "BRL"), theme.INCOME),
            (5, self._investment_cell(total_monthly_inv, "BRL"), None),
            (6, self._investment_cell(total_annual_inv, "BRL"), None),
        ]
        bold = None
        for col, text, color in cells:
            item = QTableWidgetItem(text)
            if bold is None:
                bold = item.font()
                bold.setBold(True)
            item.setFont(bold)
            if color is not None:
                item.setForeground(QColor(color))
            table.setItem(row, col, item)
