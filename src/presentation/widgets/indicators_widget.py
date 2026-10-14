from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.presentation import icons
from src.presentation.i18n import format_currency, format_date, format_number, t
from src.presentation.widgets.stat_card import make_stat_card
from src.presentation.widgets.dashboard.chart_widget import ChartWidget
from src.presentation.workers.indicator_refresh_worker import IndicatorRefreshWorker
from src.domain.services.indicator_catalog import all_keys


class IndicatorsWidget(QWidget):
    """Economic-indicator tab: a row of latest-value stat cards (USD/BRL, SELIC,
    IPCA, CDI, IGP-M), a history chart with a picker, and a threaded "Refresh"
    action that fetches from BCB off the UI thread and persists on the main
    thread (SQLite is single-thread-bound)."""

    indicators_updated = Signal()

    def __init__(self, investment_chart_data_service, indicator_use_cases, parent=None):
        super().__init__(parent)
        self._service = investment_chart_data_service
        self._indicator_use_cases = indicator_use_cases
        self._indicator_thread = None
        self._indicator_worker = None
        self._keys = all_keys()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel(t("indicators.title")))
        header.addStretch()
        self._last_fetch_label = QLabel("")
        self._last_fetch_label.setObjectName("statCardTitle")
        header.addWidget(self._last_fetch_label)
        self._refresh_btn = QPushButton(t("market.refresh"))
        self._refresh_btn.setIcon(icons.icon("fa6s.arrows-rotate"))
        self._refresh_btn.clicked.connect(self._refresh_indicators)
        header.addWidget(self._refresh_btn)
        layout.addLayout(header)

        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(8)
        layout.addLayout(self._cards_row)

        chart_header = QHBoxLayout()
        chart_header.addWidget(QLabel(t("indicators.history")))
        self._series_combo = QComboBox()
        for key in self._keys:
            info = self._service.get_indicator_info(key)
            self._series_combo.addItem(t(info.label_key) if info else key, key)
        self._series_combo.currentIndexChanged.connect(self._refresh_chart)
        chart_header.addWidget(self._series_combo)
        chart_header.addStretch()
        layout.addLayout(chart_header)

        self._chart = ChartWidget("line")
        layout.addWidget(self._chart, 1)

        self.refresh()

    # -- rendering ------------------------------------------------------------

    def refresh(self):
        self._refresh_cards()
        self._refresh_chart()
        self._update_last_fetch_label()

    def _refresh_cards(self):
        while self._cards_row.count():
            item = self._cards_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Unparent immediately so the old card stops rendering now;
                # deleteLater() alone leaves it painted until the event loop runs.
                widget.setParent(None)
                widget.deleteLater()
        for key in self._keys:
            info = self._service.get_indicator_info(key)
            value = self._service.get_indicator_latest(key)
            title = t(info.label_key) if info else key
            if info is None or value is None:
                card = make_stat_card(title, QLabel(t("market.no_data")))
            else:
                card = make_stat_card(title, QLabel(self._format_value(value, info)))
            self._cards_row.addWidget(card)

    def _refresh_chart(self):
        key = self._series_combo.currentData()
        if key is None:
            return
        info = self._service.get_indicator_info(key)
        dates, values = self._service.get_indicator_series(key)
        if info is not None:
            self._chart.set_value_format(info.unit, info.decimals, info.currency_code)
        if not dates:
            self._chart.set_empty_state(t("market.no_data"))
            return
        name = t(info.label_key) if info is not None else key
        self._chart.set_series([format_date(d) for d in dates], {name: values})

    @staticmethod
    def _format_value(value, info) -> str:
        if info.unit == "percent":
            return f"{format_number(value, info.decimals)}%"
        if info.unit == "currency":
            return format_currency(value, info.currency_code)
        return format_number(value, info.decimals)

    def _update_last_fetch_label(self):
        last_fetch = self._indicator_use_cases.get_last_fetch()
        if last_fetch:
            self._last_fetch_label.setText(
                t("market.last_updated", when=format_date(last_fetch[:10]))
            )
        else:
            self._last_fetch_label.setText(t("market.never_updated"))

    # -- indicator refresh (threaded) -----------------------------------------

    def _refresh_indicators(self):
        if self._indicator_use_cases is None or self._indicator_thread is not None:
            return
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText(t("market.refreshing"))

        self._indicator_thread = QThread(self)
        self._indicator_worker = IndicatorRefreshWorker(self._indicator_use_cases)
        self._indicator_worker.moveToThread(self._indicator_thread)
        self._indicator_thread.started.connect(self._indicator_worker.run)
        self._indicator_worker.finished.connect(self._on_indicators_refreshed)
        self._indicator_worker.failed.connect(self._on_indicators_failed)
        self._indicator_worker.done.connect(self._teardown_indicator_thread)
        self._indicator_thread.start()

    def _on_indicators_refreshed(self, result):
        # Persist on the main thread (SQLite connection is thread-bound).
        if isinstance(result, dict):
            self._indicator_use_cases.store(result.get("fetched", {}))
        self.refresh()
        self.indicators_updated.emit()
        failed = result.get("failed") if isinstance(result, dict) else None
        if failed:
            QMessageBox.warning(
                self, t("market.fetch_error.title"),
                t("market.fetch_error.body", detail="; ".join(failed.values())),
            )

    def _on_indicators_failed(self, message):
        QMessageBox.warning(
            self, t("market.fetch_error.title"),
            t("market.fetch_error.body", detail=message),
        )

    def _teardown_indicator_thread(self):
        if self._indicator_thread is not None:
            self._indicator_thread.quit()
            self._indicator_thread.wait()
            self._indicator_thread = None
            self._indicator_worker = None
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText(t("market.refresh"))
