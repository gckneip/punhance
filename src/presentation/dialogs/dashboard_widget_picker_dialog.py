from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from src.application.dashboard_presets import (
    DEFAULT_PRESETS, clone_preset_config, default_span_for_chart_type, find_preset,
)
from src.application.dto.dashboard_widget_template_dto import CreateDashboardWidgetTemplateDTO
from src.presentation.dialogs.custom_chart_builder_dialog import CustomChartBuilderDialog
from src.presentation.widgets.dashboard.generic_widget_renderer import build_generic_content
from src.presentation.widgets.dashboard.preview_drawer import PreviewDrawer

PREVIEW_PLACEHOLDER_TEXT = "Hover over a widget to preview it here."


class DashboardWidgetPickerDialog(QDialog):
    def __init__(
        self, parent=None, accounts=None, categories=None, counterparties=None,
        credit_cards=None, chart_data_service=None, dashboard_widget_template_use_cases=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Widget")
        self.setModal(True)
        self.resize(760, 480)

        self._accounts = accounts or []
        self._categories = categories or []
        self._counterparties = counterparties or []
        self._credit_cards = credit_cards or []
        self._chart_data_service = chart_data_service
        self._template_use_cases = dashboard_widget_template_use_cases
        self._result = None

        outer = QVBoxLayout(self)

        content_row = QHBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self._build_premade_tab(), "Premade")
        tabs.addTab(self._build_custom_tab(), "Custom")
        content_row.addWidget(tabs, stretch=1)
        self._preview = PreviewDrawer()
        self._preview.show_placeholder(PREVIEW_PLACEHOLDER_TEXT)
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
        for preset in DEFAULT_PRESETS:
            item = QListWidgetItem(preset.title)
            item.setData(Qt.UserRole, preset.preset_id)
            self._preset_list.addItem(item)
        self._preset_list.itemEntered.connect(lambda item: self._show_preset_preview(item.data(Qt.UserRole)))
        self._preset_list.currentItemChanged.connect(
            lambda current, _prev: self._show_preset_preview(current.data(Qt.UserRole) if current else None)
        )
        layout.addWidget(self._preset_list)

        add_btn = QPushButton("Add Selected")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_add_preset)
        layout.addWidget(add_btn)
        return panel

    def _build_custom_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("Your saved custom widgets:"))
        self._template_list = QListWidget()
        self._template_list.setMouseTracking(True)
        self._reload_templates()
        self._template_list.itemEntered.connect(lambda item: self._show_template_preview(item.data(Qt.UserRole)))
        self._template_list.currentItemChanged.connect(
            lambda current, _prev: self._show_template_preview(current.data(Qt.UserRole) if current else None)
        )
        layout.addWidget(self._template_list)

        template_btn_row = QHBoxLayout()
        add_template_btn = QPushButton("Add Selected")
        add_template_btn.setObjectName("primaryButton")
        add_template_btn.clicked.connect(self._on_add_template)
        template_btn_row.addWidget(add_template_btn)
        delete_template_btn = QPushButton("Delete Selected")
        delete_template_btn.clicked.connect(self._on_delete_template)
        template_btn_row.addWidget(delete_template_btn)
        layout.addLayout(template_btn_row)

        layout.addWidget(QLabel("Build a widget from your own metrics, filters, and date range."))
        create_btn = QPushButton("Create Custom Widget...")
        create_btn.setObjectName("primaryButton")
        create_btn.clicked.connect(self._on_create_custom)
        layout.addWidget(create_btn)
        layout.addStretch()
        return panel

    def _reload_templates(self):
        self._template_list.clear()
        if self._template_use_cases is None:
            return
        for template in self._template_use_cases.list_templates():
            item = QListWidgetItem(template.title)
            item.setData(Qt.UserRole, template.id)
            self._template_list.addItem(item)

    def _show_preset_preview(self, preset_id):
        preset = find_preset(preset_id) if preset_id else None
        if preset is None:
            self._preview.set_title("Preview")
            self._preview.show_placeholder(PREVIEW_PLACEHOLDER_TEXT)
            return

        self._preview.set_title(preset.title)
        if self._chart_data_service is None:
            self._preview.show_placeholder(PREVIEW_PLACEHOLDER_TEXT)
            return

        is_stat = preset.config.get("chart_type") == "stat"
        try:
            content = build_generic_content(preset.title, clone_preset_config(preset), self._chart_data_service)
        except Exception:
            self._preview.show_placeholder("Couldn't render a preview for this widget.")
            return
        self._preview.show_content(content, center=is_stat)

    def _show_template_preview(self, template_id):
        template = self._find_template(template_id) if template_id else None
        if template is None:
            self._preview.set_title("Preview")
            self._preview.show_placeholder(PREVIEW_PLACEHOLDER_TEXT)
            return

        self._preview.set_title(template.title)
        if self._chart_data_service is None:
            self._preview.show_placeholder(PREVIEW_PLACEHOLDER_TEXT)
            return

        is_stat = template.config.get("chart_type") == "stat"
        try:
            content = build_generic_content(template.title, dict(template.config), self._chart_data_service)
        except Exception:
            self._preview.show_placeholder("Couldn't render a preview for this widget.")
            return
        self._preview.show_content(content, center=is_stat)

    def _find_template(self, template_id):
        if self._template_use_cases is None:
            return None
        return next(
            (t for t in self._template_use_cases.list_templates() if t.id == template_id), None
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
            self, "Delete Saved Widget", f'Delete "{item.text()}" from your saved custom widgets?',
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
        preset_id = item.data(Qt.UserRole)
        preset = next(p for p in DEFAULT_PRESETS if p.preset_id == preset_id)
        self._result = {
            "title": preset.title,
            "config": clone_preset_config(preset),
            "row_span": preset.default_row_span,
            "col_span": preset.default_col_span,
            "source_preset_id": preset.preset_id,
        }
        self.accept()

    def _on_create_custom(self):
        dialog = CustomChartBuilderDialog(
            self, accounts=self._accounts, categories=self._categories,
            counterparties=self._counterparties, credit_cards=self._credit_cards,
            chart_data_service=self._chart_data_service,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        row_span, col_span = default_span_for_chart_type(data["config"]["chart_type"])

        if self._template_use_cases is not None:
            self._template_use_cases.create_template(CreateDashboardWidgetTemplateDTO(
                title=data["title"], config=data["config"], row_span=row_span, col_span=col_span,
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
