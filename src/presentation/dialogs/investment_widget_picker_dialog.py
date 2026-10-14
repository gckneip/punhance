from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from src.application.investment_presets import (
    DEFAULT_INVESTMENT_PRESETS, clone_investment_preset_config,
    default_span_for_source, find_investment_preset,
)
from src.application.dto.dashboard_widget_template_dto import CreateDashboardWidgetTemplateDTO
from src.presentation.dialogs.investment_chart_builder_dialog import InvestmentChartBuilderDialog
from src.presentation.i18n import t
from src.presentation.widgets.dashboard.investment_widget_renderer import build_investment_content
from src.presentation.widgets.dashboard.preview_drawer import PreviewDrawer

INVESTMENTS_CONTEXT = "investments"


class InvestmentWidgetPickerDialog(QDialog):
    def __init__(self, parent=None, service=None, dashboard_widget_template_use_cases=None):
        super().__init__(parent)
        self.setWindowTitle(t("widget_picker.title"))
        self.setModal(True)
        self.resize(760, 480)

        self._service = service
        self._template_use_cases = dashboard_widget_template_use_cases
        self._result = None

        outer = QVBoxLayout(self)
        content_row = QHBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self._build_premade_tab(), t("widget_picker.tab.premade"))
        tabs.addTab(self._build_custom_tab(), t("widget_picker.tab.custom"))
        content_row.addWidget(tabs, stretch=1)
        self._preview = PreviewDrawer()
        self._preview.show_placeholder(t("widget_picker.preview_hint"))
        content_row.addWidget(self._preview)
        outer.addLayout(content_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        if self._preset_list.count():
            self._preset_list.setCurrentRow(0)

    def _build_premade_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._preset_list = QListWidget()
        self._preset_list.setMouseTracking(True)
        for preset in DEFAULT_INVESTMENT_PRESETS:
            item = QListWidgetItem(t(preset.display_title_key))
            item.setData(Qt.UserRole, preset.preset_id)
            self._preset_list.addItem(item)
        self._preset_list.itemEntered.connect(lambda item: self._show_preset_preview(item.data(Qt.UserRole)))
        self._preset_list.currentItemChanged.connect(
            lambda current, _prev: self._show_preset_preview(current.data(Qt.UserRole) if current else None)
        )
        layout.addWidget(self._preset_list)

        add_btn = QPushButton(t("widget_picker.add_selected"))
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_add_preset)
        layout.addWidget(add_btn)
        return panel

    def _build_custom_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel(t("widget_picker.saved_label")))
        self._template_list = QListWidget()
        self._template_list.setMouseTracking(True)
        self._reload_templates()
        self._template_list.itemEntered.connect(lambda item: self._show_template_preview(item.data(Qt.UserRole)))
        self._template_list.currentItemChanged.connect(
            lambda current, _prev: self._show_template_preview(current.data(Qt.UserRole) if current else None)
        )
        layout.addWidget(self._template_list)

        template_btn_row = QHBoxLayout()
        add_template_btn = QPushButton(t("widget_picker.add_selected"))
        add_template_btn.setObjectName("primaryButton")
        add_template_btn.clicked.connect(self._on_add_template)
        template_btn_row.addWidget(add_template_btn)
        delete_template_btn = QPushButton(t("common.delete_selected"))
        delete_template_btn.clicked.connect(self._on_delete_template)
        template_btn_row.addWidget(delete_template_btn)
        layout.addLayout(template_btn_row)

        layout.addWidget(QLabel(t("widget_picker.build_hint")))
        create_btn = QPushButton(t("widget_picker.create_custom"))
        create_btn.setObjectName("primaryButton")
        create_btn.clicked.connect(self._on_create_custom)
        layout.addWidget(create_btn)
        layout.addStretch()
        return panel

    def _reload_templates(self):
        self._template_list.clear()
        if self._template_use_cases is None:
            return
        for template in self._template_use_cases.list_templates(INVESTMENTS_CONTEXT):
            item = QListWidgetItem(template.title)
            item.setData(Qt.UserRole, template.id)
            self._template_list.addItem(item)

    def _show_preset_preview(self, preset_id):
        preset = find_investment_preset(preset_id) if preset_id else None
        if preset is None or self._service is None:
            self._preview.set_title(t("chart.preview.title"))
            self._preview.show_placeholder(t("widget_picker.preview_hint"))
            return
        self._preview.set_title(t(preset.display_title_key))
        is_stat = preset.config.get("chart_type") == "stat"
        try:
            content = build_investment_content(
                t(preset.display_title_key), clone_investment_preset_config(preset), self._service
            )
        except Exception:
            self._preview.show_placeholder(t("widget_picker.preview_error"))
            return
        self._preview.show_content(content, center=is_stat)

    def _show_template_preview(self, template_id):
        template = self._find_template(template_id) if template_id else None
        if template is None or self._service is None:
            self._preview.set_title(t("chart.preview.title"))
            self._preview.show_placeholder(t("widget_picker.preview_hint"))
            return
        self._preview.set_title(template.title)
        is_stat = template.config.get("chart_type") == "stat"
        try:
            content = build_investment_content(template.title, dict(template.config), self._service)
        except Exception:
            self._preview.show_placeholder(t("widget_picker.preview_error"))
            return
        self._preview.show_content(content, center=is_stat)

    def _find_template(self, template_id):
        if self._template_use_cases is None:
            return None
        return next(
            (tpl for tpl in self._template_use_cases.list_templates(INVESTMENTS_CONTEXT) if tpl.id == template_id),
            None,
        )

    def _on_add_template(self):
        item = self._template_list.currentItem()
        if item is None:
            return
        template = self._find_template(item.data(Qt.UserRole))
        if template is None:
            return
        self._result = {
            "title": template.title,
            "config": dict(template.config),
            "row_span": template.row_span,
            "col_span": template.col_span,
            "source_preset_id": None,
        }
        self.accept()

    def _on_delete_template(self):
        item = self._template_list.currentItem()
        if item is None or self._template_use_cases is None:
            return
        reply = QMessageBox.question(
            self, t("widget_picker.delete.title"),
            t("widget_picker.delete.body", name=item.text()),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._template_use_cases.delete_template(item.data(Qt.UserRole))
        self._reload_templates()

    def _on_add_preset(self):
        item = self._preset_list.currentItem()
        if item is None:
            return
        preset = find_investment_preset(item.data(Qt.UserRole))
        if preset is None:
            return
        config = clone_investment_preset_config(preset)
        config["title_key"] = preset.display_title_key
        self._result = {
            "title": t(preset.display_title_key),
            "config": config,
            "row_span": preset.default_row_span,
            "col_span": preset.default_col_span,
            "source_preset_id": preset.preset_id,
        }
        self.accept()

    def _on_create_custom(self):
        dialog = InvestmentChartBuilderDialog(self, service=self._service)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        row_span, col_span = default_span_for_source(data["config"]["source"])

        if self._template_use_cases is not None:
            self._template_use_cases.create_template(CreateDashboardWidgetTemplateDTO(
                title=data["title"], config=data["config"],
                row_span=row_span, col_span=col_span, context=INVESTMENTS_CONTEXT,
            ))

        self._result = {
            "title": data["title"],
            "config": data["config"],
            "row_span": row_span,
            "col_span": col_span,
            "source_preset_id": None,
        }
        self.accept()

    def get_data(self):
        return self._result
