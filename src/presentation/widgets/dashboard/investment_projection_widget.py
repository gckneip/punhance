from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget,
)

from src.presentation.i18n import format_date, t
from src.presentation.widgets.dashboard.chart_widget import ChartWidget

# Period options offered on-screen (months).
_MONTH_OPTIONS = [6, 12, 24, 36, 60]


class _KeepOpenMenu(QMenu):
    """A QMenu that stays open when a checkable item is toggled, so the user can
    tick several assets without the menu closing after each click."""

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action is not None and action.isCheckable() and action.isEnabled():
            action.trigger()
            return
        super().mouseReleaseEvent(event)


class InvestmentProjectionWidget(QWidget):
    """Interactive investment projection: a line per selected holding, projected
    forward a selectable number of months. Both the period and the set of assets
    are chosen on-screen and persisted back into the widget config via
    on_config_change, so they survive rebuilds and restarts."""

    def __init__(self, service, config, on_config_change=None, parent=None):
        super().__init__(parent)
        self._service = service
        self._config = dict(config or {})
        self._on_config_change = on_config_change
        self._selected_ids = set(self._config.get("asset_ids") or [])
        self._months = int(self._config.get("months", 12))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        controls = QHBoxLayout()
        controls.addWidget(QLabel(t("investment.projection.period")))
        self._period_combo = QComboBox()
        for n in sorted(set(_MONTH_OPTIONS) | {self._months}):
            self._period_combo.addItem(
                t("investment.projection.n_months", n=n), n
            )
        idx = self._period_combo.findData(self._months)
        if idx >= 0:
            self._period_combo.setCurrentIndex(idx)
        self._period_combo.currentIndexChanged.connect(self._on_period_changed)
        controls.addWidget(self._period_combo)

        controls.addSpacing(12)
        controls.addWidget(QLabel(t("investment.projection.assets")))
        self._assets_button = QPushButton()
        self._assets_menu = _KeepOpenMenu(self._assets_button)
        self._assets_button.setMenu(self._assets_menu)
        controls.addWidget(self._assets_button)
        controls.addStretch()
        layout.addLayout(controls)

        self._chart = ChartWidget("line")
        self._chart.set_value_format("currency", 0, "BRL")
        layout.addWidget(self._chart)

        self._rebuild_assets_menu()
        self._render()

    # -- controls -------------------------------------------------------------

    def _rebuild_assets_menu(self):
        self._assets_menu.clear()
        holdings = self._service.get_holdings()
        valid_ids = {h.id for h in holdings}
        # Drop any persisted ids that no longer exist.
        self._selected_ids &= valid_ids
        for inv in holdings:
            action = self._assets_menu.addAction(inv.name)
            action.setCheckable(True)
            action.setChecked(inv.id in self._selected_ids)
            action.toggled.connect(lambda checked, iid=inv.id: self._on_asset_toggled(iid, checked))
        self._update_assets_button_text()

    def _update_assets_button_text(self):
        if not self._selected_ids:
            self._assets_button.setText(t("investment.projection.all_assets"))
        else:
            self._assets_button.setText(
                t("investment.projection.n_selected", n=len(self._selected_ids))
            )

    def _on_period_changed(self):
        self._months = self._period_combo.currentData()
        self._config["months"] = self._months
        self._persist()
        self._render()

    def _on_asset_toggled(self, investment_id, checked):
        if checked:
            self._selected_ids.add(investment_id)
        else:
            self._selected_ids.discard(investment_id)
        self._config["asset_ids"] = sorted(self._selected_ids)
        self._update_assets_button_text()
        self._persist()
        self._render()

    def _persist(self):
        if self._on_config_change is not None:
            self._on_config_change(dict(self._config))

    # -- render ---------------------------------------------------------------

    def _render(self):
        labels_iso, series = self._service.get_projected_value_by_asset(
            self._months, sorted(self._selected_ids) or None
        )
        if not labels_iso or not series:
            self._chart.set_empty_state(t("chart.no_data"))
            return
        labels = [format_date(d) for d in labels_iso]
        self._chart.set_series(labels, series)
